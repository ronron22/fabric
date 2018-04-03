
# -*- coding: utf-8 -*-

"""
le fait de mettre le env.host_string faite executer la commande sur la machine distante,
cela ne pose pas de problème sauf lorsque l'on effectue des opérations entre serveurs, cela
occasionne des complications parfois subtiles
"""

"""
Todo :
Gérer par exception les erreurs :
- du parsing de fichier ini - ok
- du parsing de la ligne de commande 
- du parsing Fabric - ok
Sinon
- mettre en couleur la sortie de Fabric - ok
- ajouter un changement de droit - ok
- ajouter une fonction de visualisation des différences - ok
- ajouter une option de verbosité - ok
- établir un parsing de la ligne de commande plus complet - ok
- definir des chemins personnalisés dans le conf.ini 
-  add prompting for critical tasks - ok
""" 

from fabric.api import *
from fabric.contrib.project import rsync_project
from fabric.colors import *
from fabric.context_managers import *

import argparse

from path import path

import sys

import ConfigParser

##########################
## CLI option managing  ##
##########################

parser = argparse.ArgumentParser(description='Deployment tool using Fabric and Python')

parser.add_argument("-d","--download",action="store_true",help="Download data from source server",default=None)
parser.add_argument("-u","--upload",action="store_true",help="Upload data to targets servers",default=None)
parser.add_argument("-tc","--targetcomparison",action="store_true",help="Comparison between local and the targets servers",default=None)
parser.add_argument("-sc","--sourcecomparison",action="store_true",help="Comparison between the source server and the local",default=None)
parser.add_argument("-o","--owner",action="store_true",help="Set www-data as owner",default=None)
parser.add_argument("-v","--verbose",action="store_true",help="Optionnal - increase verbosity ")
parser.add_argument("-b","--batchmode",action="store_true",help="Optionnal - set batch mode, working without prompt")
args = parser.parse_args()	

if args.verbose is True:
	verbose_enable = "-v"
else:
	verbose_enable = ""
	
#######################
## Log file managing ##
#######################

FABRIC_LOG_FILE = '/var/log/install-fabric.log' 

def addlog(x):
	try: 
		"""
		Interne - fonction de journalisation de l'excution des fonctions
		""" 
		run('echo "%s" >> %s' % (x,FABRIC_LOG_FILE))
	except:
		print(red("Impossible d'ajouter %s à %s" % (x,FABRIC_LOG_FILE)))

################################
## Configuration file parsing ##
################################

conf_file = path('conf.ini')
if not conf_file.exists() : 
	print('Unable to find the conf file %s') % conf_file
	sys.exit()

Config = ConfigParser.ConfigParser() 
Config.read('conf.ini')
try:
	targets_servers = Config.get('targets','name').split()
except:
	ConfigParser.NoSectionError
	print('Unable to find targets section or name "name" in configuration file') 
	sys.exit()

try:
	sources_servers = Config.get('sources','name').split()
except:
	ConfigParser.NoSectionError
	print('Unable to find sources section or name "name" in configuration file') 
	sys.exit()

try:
	source_path = Config.get('paths','sources_path')
except:
	ConfigParser.NoOptionError
	print('Unable to find path section or name sources_path in configuration file') 
	sys.exit()
try:
	target_path = Config.get('paths','targets_path')
except:
	ConfigParser.NoOptionError
	print('Unable to find path section or name targets_path in configuration file') 
	sys.exit()

"""
A changer en www-data
""" 
env.user  = 'root'

#########################
### Main functions ###
#########################

def syncdownloader(remotedir,localdir,server):
	with settings(hide('running','stdout','stderr'), warn_only=False):
		string_ok = 'Synchronisation from %s ok'
		string_nok = 'Unable to synchronising with %s'
		try :
			rsync_project(
				local_dir=localdir,
				remote_dir=remotedir,
				exclude='*.lst *.truc',
				delete=False,
				extra_opts=verbose_enable,
				upload=False,
				default_opts='-pthrz'
				)
			print(green(string_ok % server))
			addlog(string_ok)
		except:
			print(red(string_nok % server))
			addlog(string_nok)
			sys.exit()	

def syncuploader(localdir,remotedir,server):
	with settings(hide('running','stdout','stderr'), warn_only=True):
		string_ok = 'Synchronisation to %s ok'
		string_nok = 'Unable to synchronising with %s'
		try :
			rsync_project(
				local_dir=localdir,
				remote_dir=remotedir,
				delete=False,
				extra_opts=verbose_enable,
				exclude='*.lst *.truc',
				upload=True,
				default_opts='-pthrz'
				)
			print(green(string_ok % server))
			addlog(string_ok)
		except:
			print(red(string_nok % server))
			addlog(string_nok)
			sys.exit()	

def comparetree(remotehost,remote_dir,local_dir) :
	with settings(hide('running','stdout','stderr'), warn_only=True):
		""" 
		Il faut que les clés privées et public sans passphrases soient copiées sur TOUS les serveur.
		Sinon ca marche po
		""" 
		string_nok = 'There a problem with the server %s or the path %s'
		try:
			run("rsync -nr --out-format=%%n -e 'ssh -i /root/.ssh/id_rsa_nopass.key' %s %s:%s" % (local_dir,remotehost,remote_dir,))
		except:
			print(red(string_nok % (remotehost,remote_dir)))
			addlog(string_nok)
			sys.exit()	

def set_owner(mypath,server):
	with settings(hide('running','stdout','stderr'), warn_only=True):
		string_ok = 'Setting new owner for %s on %s is ok'
		string_nok = 'Unable to set new owner for %s on %s'
		try :
			run(('chown -R www-data:www-data %s') % mypath)
			print(green(string_ok % (mypath,server)))
			addlog(string_ok)
		except:
			print(red(string_nok % (mypath,server)))
			addlog(string_nok)
			sys.exit()	

#########################
### Running functions ###
#########################

def run_download():
        if args.batchmode is False :
                if prompt("Do you want running the download (y/n) ?", default="n", validate=r"^[YyNn]?$") in "yY":
                        pass
                else:
                        sys.exit()

	for server in sources_servers :
		env.host_string = server
		syncdownloader(source_path,target_path,server)

def run_upload() :
        if args.batchmode is False :
		if prompt("Do you want running the upload (y/n) ?", default="n", validate=r"^[YyNn]?$") in "yY":
			pass
		else:
			sys.exit()
	for server in targets_servers :
		env.host_string = server
		syncuploader(source_path,target_path,server)

def run_compare_with_targets() :
	for server in targets_servers :
		""" si l'on met env.host_string égale au serveur distant, la comparaison ce fait sur le
		serveur distant avec lui-même """
		env.host_string = 'localhost'
		comparetree(server,target_path,source_path)

def run_compare_with_sources() :
	for server in sources_servers :
		""" si l'on met env.host_string égale au serveur distant, la comparaison ce fait sur le
		serveur distant avec lui-même """
		env.host_string = 'localhost'
		comparetree(server,target_path,source_path)

def run_set_owner(mypath):
	for server in targets_servers :
		env.host_string = server
		set_owner(mypath,server)

if args.download is True:
	print ('\n downloading files from %s to localhost \n') % sources_servers
	run_download()

if args.upload is True :
	print ('\n uploading files from localhost to %s \n') % targets_servers
	run_upload()
	print ('\n Setting www-data owner to %s on %s \n') % (targets_servers,source_path)
	run_set_owner(source_path)

if args.targetcomparison is True :
	print ('\nTargets comparison between %s and localhost\n') % targets_servers 
	run_compare_with_targets()

if args.sourcecomparison is True :
	print ('\n Sources comparison between %s and localhost\n') % sources_servers
	run_compare_with_sources()
