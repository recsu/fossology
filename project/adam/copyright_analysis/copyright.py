#!/usr/bin/python

## 
## Copyright (C) 2007 Hewlett-Packard Development Company, L.P.
## 
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License
## version 2 as published by the Free Software Foundation.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License along
## with this program; if not, write to the Free Software Foundation, Inc.,
## 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
##

import re
import sys
import copyright_library as library
import cPickle as pickle
from optparse import OptionParser
import libfosspython

import psyco
psyco.full()

def main():
    #         ------------------------------------------------------------
    usage  = "%prog is used to automatically locate copyright statements. \n"
    usage += " There are three (3) possible functioning modes that %prog \n"
    usage += " can enter:\n\n"
    usage += "    MODEL CREATION    :: Create a model of copyright statements \n"
    usage += "                         using training data.\n"
    usage += "    COMMAND LINE TEST :: Test a file from the command line.\n"
    usage += "    AGENT TEST        :: Waits for commands from stdin.\n\n"
    usage += "  +----------------+\n"
    usage += "  | MODEL CREATION |\n"
    usage += "  +----------------+\n"
    usage += "  To analyze any files a model is REQUIRED. To create a model a set of labeled file must used; a basic set is provided in the data directory. First create a file listing the paths of the training files. Making sure that each training file is on its own line in the file. Next run the following command:\n"
    usage += "    %prog --model model.dat --training training_files\n"
    usage += "  This will create a model file called 'model.dat' from the training file provided in 'training_files'.\n"
    usage += "  +-------------------+\n"
    usage += "  | COMMAND LINE TEST |\n"
    usage += "  +-------------------+\n"
    usage += "  To analyze a file from the command line you must first create a model, see MODEL CREATION.\n"
    usage += "  There are two options for passing the file to be analyzed to %prog. The first uses a text file that lists the paths of the files with one path per line. The second option is to pass the files over the command line. For the first option use the following command:\n"
    usage += "    %prog --model model.dat --analyze-from-file test_files\n"

    
    usage += "  \n"
  
    optparser = OptionParser(usage)
    optparser.add_option("-m", "--model", type="string",
            help="Path to the model file.")
    optparser.add_option("-t", "--training", type="string",
            help="List of training files.")
    optparser.add_option("-f", "--analyze-from-file", type="string",
            help="Path to the files to analyze.")
    optparser.add_option("-c", "--analyze-from-command-line", action="store_true",
            help="File to be analyzed will be passed over the command line.")
    optparser.add_option("--setup-database", action="store_true",
            help="Creates the tables for copyright analysis that the fossology database needs.")
    optparser.add_option("--agent", action="store_true",
            help="Starts up in agent mode. Files will be read from stdin.")

    (options, args) = optparser.parse_args()

    if options.setup_database:
        return(setup_database())

    if not options.model:
        print >> sys.stderr, 'You must specify a model file for all phases of the algorithm.\n\n'
        optparser.print_usage()
        sys.exit(1)

    model = {}
    if options.training:
        files = [line.rstrip() for line in open(options.training).readlines()]
        model = library.create_model(files)
        pickle.dump(model, open(options.model,'w'))

    try:
        model = pickle.load(open(options.model))
    except:
        print >> sys.stderr, 'You must specify a training file to create a model.\n\n'
        optparser.print_usage()
        sys.exit(1)

    if options.analyze_from_file:
        files = [line.rstrip() for line in open(options.analyze_from_file).readlines()]
        for file in files:
            results = library.label_file(file,model)
            print "%s :: " % (file)
            if len(results) == 0:
                print "No copyrights"
            for i in range(len(results)):
                print "\t[%d:%d]" % (results[i][0], results[i][1])

    if options.analyze_from_command_line:
        files = args
        for file in files:
            results = library.label_file(file,model)
            print "%s :: " % (file)
            if len(results) == 0:
                print "No copyrights"
            for i in range(len(results)):
                print "\t[%d:%d]" % (results[i][0], results[i][1])

    if options.agent:
         return(agent())   

def agent():
    db = None
    try:
        db = libfosspython.FossDB()
    except:
        print >> sys.stderr, 'ERROR: Something is broken. Could not connect to database.'
        return 1

    line = sys.stdin.readline().strip()
    while line:
        if re.match("[0-9]+ [0-9a-f]+\.[0-9a-f]+\.[0-9]+", line):
            (pfile, file) = re.findall("([0-9]+) ([0-9a-f]+\.[0-9a-f]+\.[0-9]+)", line)[0]
            path = libfosspython.repMkPath('files', file)
            offsets = library.label_file(file,model)
            if len(offsets) == 0:
                result = db.access("INSERT INTO copyright_test (agent_fk, pfile_fk, copy_startbyte, copy_endbyte)"
                    "VALUES (1, '%s', NULL, NULL);" % (pfile))
            else:
                for i in range(len(offsets)):
                    result = db.access("INSERT INTO copyright_test (agent_fk, pfile_fk, copy_startbyte, copy_endbyte)"
                        "VALUES (1, '%s', %d, %d);" % (pfile, offsets[i][0], offsets[i][1]))
        elif re.match("quit", line):
            print "BYE."
            break
        else:
            print >> sys.stderr, "ERROR: unrecognized command."

        line = sys.stdin.readline().strip()

    return 0

def setup_database():
    db = None
    try:
        db = libfosspython.FossDB()
    except:
        print >> sys.stderr, 'ERROR: Something is broken. Could not connect to database.'
        sys.exit(1)

    result = db.access("CREATE SEQUENCE copyright_test_agent_fk_seq "
        "START WITH 1 "
        "INCREMENT BY 1 "
        "NO MAXVALUE "
        "NO MINVALUE "
        "CACHE 1;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't create copyright_test_agent_fk_seq."
        sys.exit(1)

    result = db.access("ALTER TABLE public.copyright_test_agent_fk_seq OWNER TO fossy;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't alter copyright_test_agent_fk_seq."
        sys.exit(1)

    result = db.access("CREATE SEQUENCE copyright_test_ct_pk_seq "
        "START WITH 1 "
        "INCREMENT BY 1 "
        "NO MAXVALUE "
        "NO MINVALUE "
        "CACHE 1;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't create copyright_test_ct_pk_seq."
        sys.exit(1)

    result = db.access("ALTER TABLE public.copyright_test_ct_pk_seq OWNER TO fossy;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't alter copyright_test_ct_pk_seq."
        sys.exit(1)

    result = db.access("CREATE SEQUENCE copyright_test_pfile_fk_seq "
        "START WITH 1 "
        "INCREMENT BY 1 "
        "NO MAXVALUE "
        "NO MINVALUE "
        "CACHE 1;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't create copyright_test_pfile_fk_seq."
        sys.exit(1)

    result = db.access("ALTER TABLE public.copyright_test_pfile_fk_seq OWNER TO fossy;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't alter copyright_test_pfile_fk_seq."
        sys.exit(1)

    result = db.access("CREATE TABLE copyright_test ( "
        "ct_pk bigint DEFAULT nextval('copyright_test_ct_pk_seq'::regclass) NOT NULL, "
        "agent_fk bigint DEFAULT nextval('copyright_test_agent_fk_seq'::regclass) NOT NULL, "
        "pfile_fk bigint DEFAULT nextval('copyright_test_pfile_fk_seq'::regclass) NOT NULL, "
        "copy_startbyte integer, "
        "copy_endbyte integer);")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't create license_test table."
        sys.exit(1)

    result = db.access("ALTER TABLE public.copyright_test OWNER TO fossy;")
    if result != 0:
        print >> sys.stderr, "ERROR: Couldn't alter license_test table."
        sys.exit(1)

if __name__ == '__main__':
    main()
