""" Cassandra data backup. """
import logging
import os
import sys
import tarfile
import socket

from subprocess import call
from yaml import safe_load 

sys.path.append(os.path.join(os.path.dirname(__file__), "../../lib/"))
import constants
import monit_interface

# Full path for the nodetool binary.
NODE_TOOL = '{0}/AppDB/cassandra/cassandra/bin/nodetool'.\
  format(constants.APPSCALE_HOME)

# Location where we place the tar of the nameshot.
BACKUP_DIR_LOCATION = "/opt/appscale/backups"

# File location of where the latest backup goes.
BACKUP_FILE_LOCATION = "{0}/backup.tar.gz".format(BACKUP_DIR_LOCATION)

# Cassandra monit watch name.
CASSANDRA_MONIT_WATCH_NAME = "cassandra-9999"

def clear_old_snapshots():
  """ Remove any old snapshots to minimize diskspace usage both locally. """
  call([NODE_TOOL, 'clearsnapshot'])

def create_snapshot():
  """ Perform local Cassandra backup by taking a new snapshot. """ 
  call([NODE_TOOL, 'snapshot'])

def get_snapshot_file_names():
  """ Yields all file names which should be tar'ed up.

  Returns:
    A list of files.
  """
  file_list = []
  data_dir = "{0}{1}".format(constants.APPSCALE_DATA_DIR, "cassandra")
  for what, dirnames, filenames in os.walk(data_dir):
    for file_name in filenames:
      if 'snapshots' in what:
        file_list.append(what)
  return file_list

def tar_snapshot(file_paths):
  """ Tars all snapshot files for a given snapshot name.

  Args:
    file_paths: A list of files to tar up.
  """ 
  call(["mkdir", "-p", BACKUP_DIR_LOCATION])
  call(["rm", "-f", BACKUP_FILE_LOCATION])
  tar = tarfile.open(BACKUP_FILE_LOCATION, "w:gz")
  for name in file_paths:
    tar.add(name)
  tar.close()

def get_backup_path(bucket_name):
  """ Returns the path to use when uploading to GCS.

  Args:
    bucket_name: A str, the bucket name.

  Returns:
    A str, the path to use when storing to GCS.
  """
  hostname = socket.gethostname()
  return "{0}/{1}/cassandra/".format(bucket_name, hostname)
 
def backup_data():
  """ Backup Cassandra snapshot data directories/files. """
  logging.info("Starting new backup.")
  clear_old_snapshots()
  create_snapshot()
  files = get_snapshot_file_names()
  tar_snapshot(files) 
  logging.info("Done with backup!")
  return BACKUP_FILE_LOCATION

def shut_down_cassandra():
  """ Shuts down cassandra. """
  logging.warning("Stopping Cassandra")
  monit_interface.stop(CASSANDRA_MONIT_WATCH_NAME)
  logging.warning("Done!")
 
def remove_old_data():
  """ Removes previous node data from the cassandra deployment. """
  data_dir = "{0}{1}/*".format(constants.APPSCALE_DATA_DIR, "cassandra")
  logging.warning("Removing data from {0}".format(data_dir))
  call(["rm", "-rf", data_dir])
  logging.warning("Done removing data!")

def start_cassandra():
  """ Starts up cassandra. """
  logging.warning("Starting Cassandra")
  monit_interface.start(CASSANDRA_MONIT_WATCH_NAME)
  logging.warning("Done!")

def restore_previous_backup():
  """ Restores a previous backup into the Cassandra directory structure
  from a tar ball. """
  pass
  
def restore_data():
  """ Restores the Cassandra snapshot. """
  shut_down_cassandra()
  remove_old_data()
  restore_previous_backup()
  start_cassandra()
