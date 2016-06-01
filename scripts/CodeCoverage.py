#!/usr/bin/env python

import os
import re
import sys
import argparse
import shutil
import zipfile
import ntpath
import subprocess

DEFAULT_WHITELIST = ".*cpp$" 
DEFAULT_BLACKLIST = "/usr/local/probe/.*"

CMAKEFILEPATH = "CMakeLists.txt"
LIBRARY_TO_BUILD_REGEX = 'SET\(LIBRARY_TO_BUILD (.*)\)$'

def get_file_content(filename):
   with open(filename) as f:
      content = f.readlines()
      return content

def get_library_to_build_name(line_str):
   matchObj = re.search(LIBRARY_TO_BUILD_REGEX, line_str, re.M|re.I)
   if matchObj:
      return True, matchObj.group(1)
   return False, ""

def get_project_name_from_CMakeLists_file(full_file_path):
   for line in get_file_content(filename=full_file_path):
      found, projectName = get_library_to_build_name(line_str=line)
      if found:
         return True, projectName
   return False, ""

def print_error_and_usage(argParser, error):
   print "Error:  " + error + "\n"
   print argParser.print_help()
   sys.exit(2)

def santize_input_args(arg_parser, args):
   if len(sys.argv) > 3:
      print_error_and_usage(argParser=arg_parser, error="Too many arguments supplied.")

def destroy_directory(dir_path):
   shutil.rmtree(dir_path)

def clean_and_build_directory(dir_path):
   if (os.path.exists(dir_path)):
      destroy_directory(dir_path=dir_path)
   os.makedirs(dir_path)

def remove_file_extension(filename):
   return os.path.splitext(filename)[0]
    
def strip_file_from_full_path(full_file_path):
   return ntpath.basename(full_file_path)

def unzip_file(full_file_path, directory_to_extract_to):
   to_unzip = zipfile.ZipFile(full_file_path, 'r')
   unzipped_dir_name = remove_file_extension(filename=strip_file_from_full_path(full_file_path=full_file_path))
   full_unzipped_dir_path = directory_to_extract_to + "/" + unzipped_dir_name
   if os.path.exists(full_unzipped_dir_path):
      destroy_directory(full_unzipped_dir_path)
   to_unzip.extractall(directory_to_extract_to)
   to_unzip.close() 


def run_CMake_cmd():
   CMAKE = '/usr/local/probe/bin/cmake'
   DEBUG_FLAG = '-DUSE_LR_DEBUG=ON'
   VERSION_FLAG = '-DVERSION=' + str(1)
   ARG1_FLAGS = '-DCMAKE_CXX_COMPILER_ARG1:STRING=\'-Wall -Werror -g -gdwarf-2 -fno-elide-constructors -fprofile-arcs -ftest-coverage -O0 -fPIC -m64 -Wl,-rpath -Wl,. -Wl,-rpath -Wl,/usr/local/probe/lib -Wl,-rpath -Wl,/usr/local/probe/lib64 -fno-inline -fno-inline-small-functions -fno-default-inline\''
   COMPILER_EXE_FLAG = '-DCMAKE_CXX_COMPILER=/usr/local/probe/bin/g++'
   CMAKELISTS_DIR = '..'
   CMAKE_STR = CMAKE + ' ' + DEBUG_FLAG + ' ' + VERSION_FLAG + ' ' + ARG1_FLAGS + ' ' + COMPILER_EXE_FLAG + ' ' + CMAKELISTS_DIR
   CMAKE_CMD = [CMAKE_STR]
   ret_code = subprocess.check_call(CMAKE_CMD, stderr=subprocess.STDOUT, shell=True)
   print "CMake return code: " + str(ret_code)

def compile_project():
   COMPILE_CMD = ['make -j']
   ret_code = subprocess.check_call(COMPILE_CMD, stderr=subprocess.STDOUT, shell=True)
   print "Compile return code: " + str(ret_code)

def run_UnitTestRunner(launch_dir):
   CP_RUNNER_SCRIPT = 'cp ' + launch_dir + '/scripts/unitTestRunner.sh .'
   print "CP_RUNNER_SCRIPT = " + CP_RUNNER_SCRIPT
   CP_RUNNER_SCRIPT_CMD = [CP_RUNNER_SCRIPT]
   ret_code = subprocess.check_call(CP_RUNNER_SCRIPT_CMD, stderr=subprocess.STDOUT, shell=True)
   print "Copy script return code: " + str(ret_code)
   RUNNER_SCRIPT_CMD = ['sh unitTestRunner.sh']
   try:
      ret_code = subprocess.check_call(RUNNER_SCRIPT_CMD, stderr=subprocess.STDOUT, shell=True)
   except:
      print "UnitTestRunner return code: bad"


def run_gcovr(project_name, whitelist_filter, blacklist_filter):
   GCOVR = '/usr/bin/gcovr'
   VERBOSE = '--verbose'
   SORT_PERCENTAGE = '--sort-percentage'
   FILTER = '--filter=\"'+whitelist_filter+'\"'
   EXCLUDE = '--exclude=\"'+blacklist_filter+'\"'
   GCOV_EXE = '--gcov-executable /usr/local/probe/bin/gcov'
   EXCLUDE_UNREACHABLE = '--exclude-unreachable-branches'
   HTML_FLAGS = '--html --html-details'   
   OUTPUT_FILE = '-o coverage_' + project_name + '.html'
   print "FILTER IS == " + FILTER
   print "EXCLUDE IS == " + EXCLUDE
   FLAGS = VERBOSE + ' ' + SORT_PERCENTAGE + ' ' + FILTER + ' ' + EXCLUDE + ' ' + GCOV_EXE + ' ' + EXCLUDE_UNREACHABLE + ' ' + HTML_FLAGS
   GCOVR_CMD_STR = GCOVR + ' ' + FLAGS + ' '  + OUTPUT_FILE
   try:
      ret_code = subprocess.check_call([GCOVR_CMD_STR], stderr=subprocess.STDOUT, shell=True)
   except:
      print "Gcovr return code: bad"

def copy_coverage_files_into_cov_dir(object_dir, launch_dir):
   CP_COV_FILES_STR = 'cp ' + launch_dir + '/build/CMakeFiles/' + object_dir + '/src/* ' + launch_dir +'/coverage'
   try:
      ret_code = subprocess.check_call([CP_COV_FILES_STR], stderr=subprocess.STDOUT, shell=True)
   except:
      print "Copy coverage files return code: bad"

def format_user_list(user_list):
   formatted_list = None
   if user_list is not None:
      for whitelist_item in user_list.split():
         print "Split into : " + whitelist_item
         if formatted_list is None:
            formatted_list = '.*' + whitelist_item + '$'
         else:
            formatted_list = formatted_list + '|.*'+whitelist_item+'$'
   else:
      print "list is empty"
   return formatted_list

def generate_gcovr_filter(formatted_user_list, default_list):
   if formatted_user_list is None:
      return default_list
   else:
      return default_list + '|' + formatted_user_list

def main(argv):
   argParser = argparse.ArgumentParser(description="Generate code coverage information for a Network Monitor repository that uses CMake")
   argParser.add_argument("-w", "--whitelist", dest="whitelist", metavar="HEADER_FILE", help="Whitelist a header or template file for code coverage")
   argParser.add_argument("-b", "--blacklist", dest="blacklist", metavar="SOURCE_FILE", help="Blacklist a source file for code coverage")
   
   args = argParser.parse_args()

   santize_input_args(arg_parser=argParser, args=args)
  
   foundProjectName, projectName = get_project_name_from_CMakeLists_file(full_file_path=CMAKEFILEPATH)
   if not foundProjectName:
      print "ERROR: No project name found in CMakeLists.txt"
      sys.exit(2)   

   LAUNCH_DIR = os.getcwd()
   PROJECT = projectName
   OBJ_DIR = PROJECT + '.dir'
   USER_WHITELIST = None
   USER_BLACKLIST = None
   GTEST_ZIP_PATH = LAUNCH_DIR + '/3rdparty/gtest-1.7.0.zip'

   if args.whitelist:
      USER_WHITELIST = args.whitelist
      print "USER_WHITELIST = " + USER_WHITELIST
   if args.blacklist:
      USER_BLACKLIST = args.blacklist
      print "USER_BLACKLIST = " + USER_BLACKLIST

   unzip_file(full_file_path=GTEST_ZIP_PATH, directory_to_extract_to="3rdparty")

   clean_and_build_directory(dir_path="coverage")
   clean_and_build_directory(dir_path="build")

   os.chdir(LAUNCH_DIR + '/build')
   run_CMake_cmd()
   compile_project()
   run_UnitTestRunner(launch_dir=LAUNCH_DIR)
   os.chdir(LAUNCH_DIR + '/coverage')
   
   gcovr_whitelist = generate_gcovr_filter(formatted_user_list=format_user_list(user_list=USER_WHITELIST), default_list=DEFAULT_WHITELIST)
   gcovr_blacklist = generate_gcovr_filter(formatted_user_list=format_user_list(user_list=USER_BLACKLIST), default_list=DEFAULT_BLACKLIST)
   copy_coverage_files_into_cov_dir(object_dir=OBJ_DIR, launch_dir=LAUNCH_DIR)
   run_gcovr(project_name=PROJECT, whitelist_filter=gcovr_whitelist, blacklist_filter=gcovr_blacklist)

if __name__ == '__main__':
    main(sys.argv[1:])