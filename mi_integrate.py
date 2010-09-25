#################################################################
#                                                               #
# Integrate images with MOSFLM and merge with SCALA             #
#                                                               #
# Copyright: Molecular Images   2007                            #
#                                                               #
# This script is distributed under the same conditions as MIFit #
#                                                               #
#################################################################

import sys
import os
import getopt
import time
import string
import dircache
import ccp4check

def Usage():
    print "Usage: %s [options]" % sys.argv[0]
    print "Options are:"
    print "  -t,--template_image=FILE:         name of template image file"
    print "  -s,--spacegroup=NUM               the space group number"
    print "  -f,--first_image=NUM              first image number to process, has default"
    print "  -l,--last_image=NUM               last image number to process, has default"
    print "  -i,--integrate_resolution=STRING  integrate resolution, if any"
    print "  -g,--batch_prefix=NUM             group number, prefix for batch. default: 1"
    print "  -o,--index_only=no or yes         only test index the images. default: no"
    print "  -w,--workdir=DIR                  the working directory. default: image directory"
    print "  -d,--detector_constants=FILE      file for detector constants: default: none"
    print "  -?,--help                         this help message"

def Run(argv=None):
    if argv is None:
        argv=sys.argv
        
    # Initialize

    first_image = 'none'
    last_image = 'none'
    dt_spacegroup = 'none'
    image_name = 'none'
    final_workdir = 'none'
    integrate_res = 'none'
    merging_res = 'none'
    index_only = 'no'
    integrate_res = 'none'
    batch_prefix = 'none'
    detector_constants = 'none'
    beam_x_image = 'none'
    beam_y_image = 'none'
    image_extension = 4
    gain = '1.0'

    quote = '''"'''

    ##################
    # Parse args     #
    ##################
    
    args = argv[1:]
    optlist, args = getopt.getopt(
        args,'t:s:w:f:l:i:m:g:o:d:?',
        ['template_image=','spacegroup=','first_image=',
         'last_image=','integrate_resolution=','merge_resolution=',
         'batch_prefix=','index_only=','workdir=','detector_constants=',
         'help'])
    number_of_inputs = len(optlist)
    if number_of_inputs==0:
        Usage()
        return
    count = 0
    while count < number_of_inputs:
        aList = optlist[count]
        number_of_list_inputs = len(aList)
        if number_of_list_inputs >=1:
            arg_value = aList[0]
        if arg_value=='-?' or arg_value=='--help':
            Usage()
            return
        if number_of_list_inputs >=2:
            param_value = aList[1]
            if arg_value == '-t' or arg_value=='--template_image':
                image_name = param_value
            elif arg_value == '-s' or arg_value=='--spacegroup':
                dt_spacegroup = param_value
            elif arg_value == '-f' or arg_value=='--first_image':
                first_image = param_value
            elif arg_value == '-l' or arg_value=='--last_image':
                last_image = param_value
            elif arg_value == '-i' or arg_value=='--integrate_resolution':
                integrate_res = param_value
            elif arg_value == '-g' or arg_value=='--batch_prefix':
                batch_prefix = param_value
            elif arg_value == '-o' or arg_value=='--index_only':
                index_only = param_value
            elif arg_value == '-w' or arg_value=='--workdir':
                final_workdir = param_value
            elif arg_value == '-d' or arg_value=='--detector_constants':
                detector_constants = param_value                
        count = count + 1        

    #######################
    # Checks and defaults #
    #######################        

    ccp4,error = ccp4check.ccp4check()
    if not ccp4:
        print '\n' + error + '\n'
        time.sleep(4)
        return 1

    ipmosflm_path = 'ipmosflm'

    # Check for image directory

    fileexists = os.path.exists(image_name)
    if fileexists == 0:
        print 'The template image was not found:',image_name
        time.sleep(4)
        return 1

    # Check for processed file directory

    filexists = os.path.exists(final_workdir)
    if fileexists == 0 and final_workdir != 'none':
        print 'The final directory for processed data was not found:',final_workdir
        time.sleep(4)
        return 1

    # Check for space group

    if dt_spacegroup == 'none':
        print 'The space group number was not given'
        time.sleep(4)
        return 1

    # Set data run identification

    if batch_prefix == 'none':
        data_code_number = '1'
    else:
        data_code_number = batch_prefix

    ####################################################
    # Establish image template from example image file #
    ####################################################

    image_dir = os.path.dirname(image_name)
    image_name = os.path.basename(image_name)

    # Check that image files have extension .img or .osc preceeded by a 3 or 4 digit number

    if image_name.find('.img') > -1 or image_name.find('.osc') > -1:
        
        image_name_split = image_name.split('.')
        image_name_root = image_name_split[0]
        i_end = len(image_name_root)
        i_start = i_end - 4
        image_number = image_name_root[i_start:i_end]

        if image_number.isdigit() == 1:               
            image_number = int(image_number)
            image_extension = 4
        else:
            i_start = i_end - 3
            image_number = image_name_root[i_start:i_end]
            image_extension = 3

            if image_number.isdigit() == 1:
                image_number = int(image_number)
            else:
                print '\nImage file names must contain 3 or 4 digits preceeding extension .osc/.img\n'
                time.sleep(4)
                return 1
            
        # Establish MOSFLM template file name

        num = len(image_name)

        if image_extension == 3:
            num = num - 7
            hashes = '###'
        elif image_extension == 4:
            num = num - 8
            hashes = '####'

        image_name_nodigits = image_name[0:num]

        if image_name.find('.img') > -1:
            mosflm_template = image_name_nodigits + hashes + '.img'
        elif image_name.find('.osc') > -1:
            mosflm_template = image_name_nodigits + hashes + '.osc'

        filename_spt = image_name[0:num-1] + '.spt'

    else:

        print '\nImage file names must contain 3 or 4 digits preceeding extension .osc/.img\n'
        time.sleep(4)
        return 1       

    #############################################
    # Check image folder to find image ranges   #
    #############################################

    image_number_low  = 9999
    image_number_high = -9999

    aList_dir = dircache.listdir(image_dir)
    number_files = len(aList_dir)

    count = 0
    while count < number_files:
        imagefile = aList_dir[count]
        imagefile = os.path.basename(imagefile)

        if imagefile.find('.img') > -1 or imagefile.find('.osc') > -1:
            
            if imagefile.find(image_name_nodigits) > -1:

                imagefilename_length = len(imagefile)
                
                if image_extension == 3:
                    i1 = imagefilename_length - 7
                    i2 = imagefilename_length - 4
                elif image_extension  == 4:
                    i1 = imagefilename_length - 8
                    i2 = imagefilename_length - 4
                
                image_number = imagefile[i1:i2]
                
                if image_number.isdigit() == 1:
                    image_number = int(image_number)

                    if image_number < image_number_low:
                        image_number_low = image_number

                    if image_number > image_number_high:
                        image_number_high = image_number

        count = count + 1

    # Checks
        
    if image_number_low == 9999:
        print '\nFirst image number was not determined\n'
        time.sleep(4)
        return 1           

    if image_number_high == -9999:
        print '\nLast image number was not determined\n'
        time.sleep(4)
        return 1 

    # Set image numbers to integrate per user specification else use all images from directory analysis

    if first_image != 'none':
        image_number_low = int(first_image)
    else:
        first_image = str(image_number_low)
    
    if last_image != 'none':
        image_number_high = int(last_image)
    else:
        last_image = str(image_number_high)

    #############################
    # Setup program parameters  #
    #############################

    # Total number of images

    number_images = image_number_high - image_number_low + 1

    if number_images < 10:
        print '\nImages in this data set only', str(image_number_low), ' to ', str(image_number_high),' so not processing\n'
        time.sleep(4)
        return 1            

    # Starting indexing and refinement images

    index_first = image_number_low
    refine_segment1_first = image_number_low
    refine_segment1_last = image_number_low + 3
    cell_refine_images_segment1 = str(refine_segment1_first) + ' to ' + str(refine_segment1_last)

    # Orthogonal images for refinement

    second_index = 90

    if number_images > second_index:
        index_second = image_number_low + second_index - 1
        refine_segment2_last = image_number_low + second_index -1
 
    else:
        index_second = image_number_high
        refine_segment2_last = image_number_high

    refine_segment2_first = refine_segment2_last - 3
    cell_refine_images_segment2 = str(refine_segment2_first) + ' to ' + str(refine_segment2_last)   

    # Intermediate images for refinement

    refine_segment12_first = (refine_segment1_first + refine_segment2_first)/2
    refine_segment12_first = int(refine_segment12_first)    
    refine_segment12_last = refine_segment12_first + 3
    cell_refine_images_segment12 = str(refine_segment12_first) + ' to ' + str(refine_segment12_last)    

    # Orthogonal images ranges for initial index and for possible reindexing pass

    image_seq_find = str(index_first) + ' ' + str(index_second)
    image_seq_reindex = str(index_first) + ' ' + str(refine_segment12_first) + ' ' + str(index_second) 

    # Collect user-defined beamcenter or distance data from a special constants file

    beam_x = 'none'
    beam_y = 'none'
    xtal_detector_distance = 'none'

    fileexists = os.path.exists(detector_constants)
    if fileexists != 0 and detector_constants != 'none':

        file = open(detector_constants,'r')
        allLines = file.readlines()
        file.close()

        for eachLine in allLines:

            if eachLine.find('beam_center') > -1:
                aLine = eachLine.split()
                number_args = len(aLine)
                if number_args > 2:
                    beam_x = aLine[1]
                    beam_y = aLine[2] 
                else:
                    print 'There should be two numbers on the beam_center line'
                    time.sleep(4)
                    return 1

            if eachLine.find('xtal_detector_distance') > -1:
                aLine = eachLine.split()
                number_args = len(aLine)

                if number_args > 1:
                    xtal_detector_distance = aLine[1]
                else:
                    print 'There should be one number on the xtal_detector_distance line'
                    time.sleep(4)
                    return 1

            if eachLine.find('detector_gain') > -1:
                aLine = eachLine.split()
                number_args = len(aLine)

                if number_args > 1:
                    detector_gain = aLine[1]
                else:
                    print 'There should be one number on the detector_gain line'
                    time.sleep(4)
                    return 1

    ##########
    # Start  #
    ##########

    print '\nAutomated integration and merging\n'
    print 'Image directory:',image_dir
    print 'Template image:',mosflm_template
    print 'Batch number:',batch_prefix
    print 'First image to process:',first_image
    print 'Last image to process:',last_image
    print 'Images for initial indexing:',image_seq_find
    print 'Integration resolution limits:',integrate_res
    if integrate_res == 'none':
        print ' It may be better to specify the resolution limits'
    print 'Expected space group number:',dt_spacegroup

    if beam_x != 'none':
        print 'Using input beam center:',beam_x,beam_y

    if xtal_detector_distance != 'none':
        print 'Using input detector distance:',xtal_detector_distance

    # Go to image directory

    os.chdir(image_dir)

    # Process log

    runtime = time.ctime(time.time())

    file = open('autoprocess.log','w')
    file.write('Processing start time       : ')
    file.write(runtime)
    file.write('\n')
    file.close()

    # Eliminate debris from previous runs

    fileexists = os.path.exists('COORDS')
    if fileexists != 0:
        os.remove('COORDS')

    fileexists = os.path.exists('SUMMARY')
    if fileexists != 0:
        os.remove('SUMMARY')

    fileexists = os.path.exists('NEWMAT')
    if fileexists != 0:
        os.remove('NEWMAT')

    fileexists = os.path.exists('NEWMAT_REFINED')
    if fileexists != 0:
        os.remove('NEWMAT_REFINED')

    ###############
    # Check index #
    ###############

    if index_only == 'yes':

        runtime = time.ctime(time.time())
        print 'Date:',runtime
        print 'Indexing test'

        file = open('mi_mosflm_index_check.inp','w')

        file.write('TITLE Indexing check in P1\n')
        file.write('TEMPLATE ')
        file.write(mosflm_template)
        file.write('\n') 
        file.write('DIRECTORY "')
        file.write(image_dir)
        file.write('"\n')

        # Apply user specified beam center if given

        if beam_x != 'none':
            file.write('BEAM ')
            file.write(beam_x)
            file.write(' ')
            file.write(beam_y)
            file.write('\n')

        # Apply user specified distance if given

        if xtal_detector_distance != 'none':
            file.write('DISTANCE ')
            file.write(xtal_detector_distance)
            file.write('\n')

        # Symmetry and indexing

        file.write('SYMM 1\n')
        file.write('SEPARATION CLOSE\n')
        file.write('FINDSPOTS THRESHOLD 10\n')       
        file.write('AUTOINDEX DPS IMAGES ')
        file.write(image_seq_find)
        file.write('\n')
        file.write('GO\n')
        file.close()

        # Execute

        runmosflm = ipmosflm_path + ' < mi_mosflm_index_check.inp > mi_mosflm_index_check.log'
        os.system(runmosflm)

        fileexists = os.path.exists('NEWMAT')
        if fileexists != 0:
            os.remove('mi_mosflm_index_check.inp')

        else:

            print 'MOSFLM Indexing check seems to have failed'
            time.sleep(4)
            return 1

        fileexists = os.path.exists('COORDS')
        if fileexists != 0:
            os.remove('COORDS')

        fileexists = os.path.exists('SUMMARY')
        if fileexists != 0:
            os.remove('SUMMARY')

        fileexists = os.path.exists('NEWMAT')
        if fileexists != 0:
            os.remove('NEWMAT')       

        print 'Testing indexing only. See file: mi_mosflm_index_check.log'
        time.sleep(4)
        return 1

    ###############
    # Auto index  #
    ###############

    indexed = 'yes'

    runtime = time.ctime(time.time())
    print 'Date:',runtime
    print 'Autoindexing'

    file = open('mi_mosflm_index.inp','w')

    file.write('TITLE Autoindexing\n')
    file.write('TEMPLATE ')
    file.write(mosflm_template)
    file.write('\n') 
    file.write('DIRECTORY "')
    file.write(image_dir)
    file.write('"\n')

    # Apply user specified beam center if given

    if beam_x != 'none':
        file.write('BEAM ')
        file.write(beam_x)
        file.write(' ')
        file.write(beam_y)
        file.write('\n')

    # Apply user specified distance if given

    if xtal_detector_distance != 'none':
        file.write('DISTANCE ')
        file.write(xtal_detector_distance)
        file.write('\n')

    # Symmetry and indexing

    file.write('SYMM ')
    file.write(dt_spacegroup)
    file.write('\n')
    file.write('SEPARATION CLOSE\n')
    file.write('FINDSPOTS THRESHOLD 10\n')       
    file.write('AUTOINDEX DPS IMAGES ')
    file.write(image_seq_find)
    file.write('\n')
    file.write('GO\n')
    file.close()

    # Execute

    runmosflm = ipmosflm_path + ' < mi_mosflm_index.inp > mi_mosflm_index.log'
    os.system(runmosflm)

    fileexists = os.path.exists('NEWMAT')
    if fileexists != 0:

        os.remove('mi_mosflm_index.inp')

        runtime = time.ctime(time.time())

        file = open('autoprocess.log','a')
        file.write('Autoindexing done           : ')
        file.write(runtime)
        file.write('\n')
        file.close()

        # Obtain beam center

        file = open('mi_mosflm_index.log')   
        allLines = file.readlines()
        file.close()

        for eachLine in allLines:
            if eachLine.find('Beam coordinates of') > -1 and eachLine.find('have been refined') > -1:
                aLine = eachLine.split()
                beam_x_image = aLine[9]
                beam_y_image = aLine[10]

            if eachLine.find('***** WARNING ***** WARNING ***** WARNING') > -1:
                indexed = 'no'

        if beam_x_image == 'none' or beam_y_image == 'none':
            print 'Parsing of beam center seems to have failed'
            time.sleep(4)
            return 1

    else:

        print 'MOSFLM Autoindexing seems to have failed'
        time.sleep(4)
        return 1

    fileexists = os.path.exists('COORDS')
    if fileexists != 0:
        os.remove('COORDS')

    fileexists = os.path.exists('SUMMARY')
    if fileexists != 0:
        os.remove('SUMMARY')

    if indexed == 'no':
        print 'There appears to be a problem with the direct beam position - stopping'
        time.sleep(4)
        return 1
    
    #####################
    # Cell Refinement   #
    #####################

    refined = 'yes'

    runtime = time.ctime(time.time())
    print 'Date:',runtime
    print 'Cell refinement' 

    file = open('mi_mosflm_refine.inp','w')

    file.write('TITLE Cell refinement\n')
    file.write('TEMPLATE ')
    file.write(mosflm_template)
    file.write('\n') 
    file.write('DIRECTORY "')
    file.write(image_dir)
    file.write('"\n')
    file.write('MATRIX NEWMAT\n')

    # Use beam center from indexing
    
    file.write('BEAM ')
    file.write(beam_x_image)
    file.write(' ')
    file.write(beam_y_image)
    file.write('\n')
    file.write('BACKSTOP CENTRE ')
    file.write(beam_x_image)
    file.write(' ')
    file.write(beam_y_image)
    file.write(' RADIUS 5.00\n')

    # Apply user specified distance if given

    if xtal_detector_distance != 'none':
        file.write('DISTANCE ')
        file.write(xtal_detector_distance)
        file.write('\n')

    file.write('SYMM ')
    file.write(dt_spacegroup)
    file.write('\n')

    # Machine and crystal default

    file.write('MOSAIC 0.70\n')
    file.write('SEPARATION CLOSE\n')      
    file.write('GAIN ')
    file.write(gain)
    file.write('\n')
    file.write('OVERLOAD CUTOFF 65500\n')
    file.write('DISTORTION YSCALE 1.0000 TILT 0 TWIST 0\n')

    if integrate_res != 'none':
        file.write('RESOLUTION ')
        file.write(integrate_res)
        file.write('\n')
        
    # Refinement

    file.write('NEWMATRIX NEWMAT_REFINED\n')
    file.write('POSTREF SEGMENT 3 MAXRESIDUAL 1.3 SHIFTFAC 3.0 MAXSHIFT 0.1 RESOLUTION 4.0\n')    
    file.write('PROCESS ')
    file.write(cell_refine_images_segment1)
    file.write('\nGO\n')
    file.write('PROCESS ')
    file.write(cell_refine_images_segment12)
    file.write('\nGO\n')
    file.write('PROCESS ')
    file.write(cell_refine_images_segment2)
    file.write('\nGO\n')
    file.close()

    # Execute

    runmosflm = ipmosflm_path +  ' < mi_mosflm_refine.inp > mi_mosflm_refine.log'
    os.system(runmosflm)

    fileexists = os.path.exists('NEWMAT_REFINED')
    if fileexists != 0:

        os.remove('mi_mosflm_refine.inp')

        runtime = time.ctime(time.time())

        file = open('autoprocess.log','a')
        file.write('Cell refinement done        : ')
        file.write(runtime)
        file.write('\n')
        file.close()

        # Check cell refinement

        file = open('mi_mosflm_refine.log')   
        allLines = file.readlines()
        file.close()

        for eachLine in allLines:
            if eachLine.find('INACCURATE CELL PARAMETERS') > -1:
                refined = 'no'
    else:

        print 'MOSFLM cell refinement seems to have failed'
        time.sleep(4)
        return 1

    fileexists = os.path.exists('SUMMARY')
    if fileexists != 0:
        os.remove('SUMMARY')

    fileexists = os.path.exists('GENFILE')
    if fileexists != 0:
        os.remove('GENFILE')

    fileexists = os.path.exists('NEWMAT')
    if fileexists != 0:
        os.remove('NEWMAT')

    if refined == 'no':
        
        print 'Cell parameters unreliable so trying indexing strategy'

        runtime = time.ctime(time.time())
        print 'Date:',runtime
        print 'Cell estimation' 

        # Try rescue strategy with indexing

        fileexists = os.path.exists('NEWMAT_REFINED')
        if fileexists != 0:
            os.remove('NEWMAT_REFINED')

        file = open('mi_mosflm_reindex.inp','w')

        file.write('TITLE Reindexing\n')
        file.write('TEMPLATE ')
        file.write(mosflm_template)
        file.write('\n') 
        file.write('DIRECTORY "')
        file.write(image_dir)
        file.write('"\n')
        file.write('BEAM ')
        file.write(beam_x_image)
        file.write(' ')
        file.write(beam_y_image)
        file.write('\n')

        if xtal_detector_distance != 'none':
            file.write('DISTANCE ')
            file.write(xtal_detector_distance)
            file.write('\n')

        file.write('SYMM ')
        file.write(dt_spacegroup)
        file.write('\n')
        file.write('SEPARATION CLOSE\n')
        file.write('FINDSPOTS THRESHOLD 10\n')       
        file.write('AUTOINDEX DPS IMAGES ')
        file.write(image_seq_reindex)
        file.write('\n')
        file.write('GO\n')
        file.close()

        # Execute

        runmosflm = ipmosflm_path + ' < mi_mosflm_reindex.inp > mi_mosflm_reindex.log'
        os.system(runmosflm)

        runtime = time.ctime(time.time())

        file = open('autoprocess.log','a')
        file.write('Cell reestimation done      : ')        
        file.write(runtime)
        file.write('\n')
        file.close()

        fileexists = os.path.exists('COORDS')
        if fileexists != 0:
            os.remove('COORDS')

        fileexists = os.path.exists('SUMMARY')
        if fileexists != 0:
            os.remove('SUMMARY')

        fileexists = os.path.exists('mi_mosflm_reindex.inp')
        if fileexists != 0:
            os.remove('mi_mosflm_reindex.inp')

        os.rename('NEWMAT','NEWMAT_REFINED')

    ###########################
    # Integrate               #
    ###########################

    fileexists = os.path.exists('mi_integrate.mtz')
    if fileexists != 0:
        os.remove('mi_integrate.mtz')

    runtime = time.ctime(time.time())
    print 'Date:',runtime
    print 'Image integration' 

    output_integrate_log = 'mi_mosflm_integrate_' + data_code_number + '.log'

    file = open('mi_mosflm_integrate.inp','w')

    file.write('TITLE Cell refinement\n')
    file.write('TEMPLATE ')
    file.write(mosflm_template)
    file.write('\n') 
    file.write('DIRECTORY "')
    file.write(image_dir)
    file.write('"\n')
    file.write('MATRIX NEWMAT_REFINED\n')
    file.write('GENFILE GENFILE\n')
    file.write('HKLOUT mi_integration.mtz\n')

    file.write('BEAM ')
    file.write(beam_x_image)
    file.write(' ')
    file.write(beam_y_image)
    file.write('\n')
    file.write('BACKSTOP CENTRE ')
    file.write(beam_x_image)
    file.write(' ')
    file.write(beam_y_image)
    file.write(' RADIUS 5.00\n')

    # Apply user specified distance if given

    if xtal_detector_distance != 'none':
        file.write('DISTANCE ')
        file.write(xtal_detector_distance)
        file.write('\n')

    file.write('SYMM ')
    file.write(dt_spacegroup)
    file.write('\n')

    # Machine and crystal default

    file.write('MOSAIC 0.70\n')
    file.write('GAIN ')
    file.write(gain)
    file.write('\n')
    file.write('OVERLOAD CUTOFF 65500\n')
    file.write('DISTORTION YSCALE 1.0000 TILT 0 TWIST 0\n')

    # Refinement

    if integrate_res != 'none':
        file.write('RESOLUTION ')
        file.write(integrate_res)
        file.write('\n') 

    file.write('POSTREF FIX ALL\n')
    file.write('PROCESS ')
    file.write(first_image)
    file.write(' TO ')
    file.write(last_image)
    file.write('\nGO\n')
    file.close()

    # Execute

    runmosflm = ipmosflm_path + ' < mi_mosflm_integrate.inp > ' + output_integrate_log
    os.system(runmosflm)

    fileexists = os.path.exists('mi_integration.mtz')
    if fileexists != 0:
        os.remove('mi_mosflm_integrate.inp')
    else:
        print 'MOSFLM integration seems to have failed'
        time.sleep(4)
        return 1

    fileexists = os.path.exists('SUMMARY')
    if fileexists != 0:
        os.remove('SUMMARY')

    fileexists = os.path.exists('GENFILE.gen')
    if fileexists != 0:
        os.remove('GENFILE.gen')

    fileexists = os.path.exists('NEWMAT_REFINED')
    if fileexists != 0:
        os.remove('NEWMAT_REFINED')
        
    fileexists = os.path.exists(filename_spt)
    if fileexists != 0:
        os.remove(filename_spt)

    #################################
    # Need to sort prior to merging #
    #################################

    fileexists = os.path.exists('mi_integration_sorted.mtz')
    if fileexists != 0:
        os.remove('mi_integration_sorted.mtz')

    file = open('mi_sortmtz.inp','w')

    file.write('H K L M/ISYM BATCH\n')
    file.close()

    run_sortmtz = 'sortmtz HKLIN mi_integration.mtz HKLOUT mi_integration_sorted.mtz < mi_sortmtz.inp > mi_sortmtz.log'

    os.system(run_sortmtz)

    fileexists = os.path.exists('mi_integration_sorted.mtz')
    if fileexists == 0:
        print 'Sorting process failed'
        time.sleep(4)
        return 1
    else:
        os.remove('mi_integration.mtz')
        os.rename('mi_integration_sorted.mtz','mi_integration.mtz')
        os.remove('mi_sortmtz.inp')
        os.remove('mi_sortmtz.log')

    # Check

    fileexists = os.path.exists('mi_integration.mtz')
    if fileexists == 0:
        print 'File mi_integration.mtz is not available for merging'
        time.sleep(4)
        return 1
    else:
        runtime = time.ctime(time.time())

        file = open('autoprocess.log','a')
        file.write('Integration done            : ')
        file.write(runtime)
        file.write('\n')
        file.close()

    #########################################################
    # Automatic assessment of resolution limit if not given #
    #########################################################

    if integrate_res == 'none':

        ioversigi_limit = 2.0

        runtime = time.ctime(time.time())

        print 'Date:',runtime
        print 'Merging test'

        output_ref_initial = 'ScalAverage_' + data_code_number + '_initial.mtz'
        output_log_initial = 'scala_scaleaverage_' + data_code_number + '_initial.log'        

        file = open('mi_scala.inp','w')
        file.write('TITLE First pass merging\n')
        file.write('RUN 1 ALL\n')
        file.write('INTENSITIES PARTIAL\n')
        file.write('CYCLES 20\n')
        file.write('ANOMALOUS OFF\n')
        file.write('SDCORRECTION 1.3 0.02\n')  
        file.write('SCALES ROTATION SPACING 5 SECONDARY 6 TAILS BFACTOR ON BROTATION SPACING 20\n')
        file.write('TIE BFACTOR 0.5\n')
        file.write('REJECT 6 6 ALL -8 -8\n')   
        file.write('EXCLUDE EMAX 10\n')
        file.write('BINS 20\n')
        file.close()

        run_scala = 'scala HKLIN mi_integration.mtz HKLOUT ' + output_ref_initial +\
                    ' SCALES mi_scales.txt ROGUES mi_rogues.txt NORMPLOT mi_normplot.txt PLOT mi_plot.txt < mi_scala.inp > ' \
                     + output_log_initial

        os.system(run_scala)

        fileexists = os.path.exists(output_ref_initial)
        if fileexists == 0:    
            print 'Process SCALA seems to have failed'
            time.sleep(4)
            return 1
        else:

            os.remove('mi_scala.inp')

            runtime = time.ctime(time.time())

            file = open('autoprocess.log','a')
            file.write('Merging check done          : ')            
            file.write(runtime)
            file.write('\n')
            file.close()

        # Clean

        fileexists = os.path.exists(output_ref_initial)
        if fileexists == 1:
            os.remove(output_ref_initial)        

        fileexists = os.path.exists('mi_scales.txt')
        if fileexists == 1:
            os.remove('mi_scales.txt')

        fileexists = os.path.exists('mi_rogues.txt')
        if fileexists == 1:
            os.remove('mi_rogues.txt')

        fileexists = os.path.exists('mi_normplot.txt')
        if fileexists == 1:
            os.remove('mi_normplot.txt')

        fileexists = os.path.exists('mi_plot.txt')
        if fileexists == 1:
            os.remove('mi_plot.txt')

        fileexists = os.path.exists('fort.10')
        if fileexists == 1:
            os.remove('fort.10')

        fileexists = os.path.exists('COORDS')
        if fileexists == 1:
            os.remove('COORDS')

        fileexists = os.path.exists('ROGUEPLOT')
        if fileexists == 1:
            os.remove('ROGUEPLOT')

        fileexists = os.path.exists('CORRELPLOT')
        if fileexists == 1:
            os.remove('CORRELPLOT')        

        # Capture table data to check merging

        aList_res_high = []
        aList_ioversigi = []
        table_length = 0
        read_table = 'no'
        parse_table = 'no'

        file = open(output_log_initial,'r')
        allLines = file.readlines()
        file.close()

        for eachLine in allLines:

            aLine = eachLine.split()

            if parse_table == 'yes':

                num_entries = len(aLine)
                
                if num_entries > 12:
                    res_high = aLine[2]
                    ioversigi = aLine[12]
                    aList_res_high.append(res_high)
                    aList_ioversigi.append(ioversigi)
                    
            # Find table segment

            if eachLine.find('N 1/d^2 Dmin(A) Rmrg  Rfull   Rcum  Ranom  Nanom    Av_I  SIGMA I/sigma   sd Mn(I/sd)') > -1:
                read_table = 'yes'
                
            if parse_table == 'yes' and aLine[0] == '$$':
                read_table = 'no'
                parse_table = 'no'

            if read_table == 'yes' and aLine[0] == '$$':
                parse_table = 'yes'

        # Analyse table

        table_length = len(aList_res_high)

        count = 0
        while count < table_length:

            res_high = aList_res_high[count]
            ioversigi = aList_ioversigi[count]
            
            if ioversigi.find('.') > -1:
            
                res_high = float(res_high)
                ioversigi = float(ioversigi)

                # Get optimal resolution

                if ioversigi > ioversigi_limit and res_high < 3.5:
                    merging_res = res_high
                    merging_res = str(merging_res)

            count = count + 1

        print 'Using estimated resolution:',merging_res,'A'

        fileexists = os.path.exists(output_log_initial)
        if fileexists == 1:
            os.remove(output_log_initial)

    ###############################################################
    # Scale and average the integrated and profile-fitted reflns  #
    ###############################################################

    runtime = time.ctime(time.time())

    print 'Date:',runtime
    print 'Merging'

    output_ref = 'ScalAverage_' + data_code_number + '.mtz'
    output_log = 'scala_scaleaverage_' + data_code_number + '.log'

    file = open('mi_scala.inp','w')

    file.write('TITLE First pass merging\n')
    file.write('RUN 1 ALL\n')
    file.write('INTENSITIES PARTIAL\n')
    file.write('CYCLES 20\n')
    file.write('ANOMALOUS OFF\n')
    file.write('SDCORRECTION 1.3 0.02\n')  
    file.write('SCALES ROTATION SPACING 5 SECONDARY 6 TAILS BFACTOR ON BROTATION SPACING 20\n')
    file.write('TIE BFACTOR 0.5\n')
    file.write('REJECT 6 6 ALL -8 -8\n')   
    file.write('EXCLUDE EMAX 10\n')

    if merging_res != 'none':

        file.write('RESOLUTION ')
        file.write(merging_res)
        file.write('\n')

    file.close()

    run_scala = 'scala HKLIN mi_integration.mtz HKLOUT ' + output_ref +\
                ' SCALES mi_scales.txt ROGUES mi_rogues.txt NORMPLOT mi_normplot.txt PLOT mi_plot.txt < mi_scala.inp > ' \
                 + output_log

    os.system(run_scala)

    fileexists = os.path.exists(output_ref)
    if fileexists == 0:    
        print 'Process SCALA seems to have failed'
        time.sleep(4)
        return 1
    else:

        os.remove('mi_scala.inp')

        runtime = time.ctime(time.time())

        file = open('autoprocess.log','a')
        file.write('Merging done                : ')
        file.write(runtime)
        file.write('\n')
        file.close()

    fileexists = os.path.exists('mi_scales.txt')
    if fileexists == 1:
        os.remove('mi_scales.txt')

    fileexists = os.path.exists('mi_rogues.txt')
    if fileexists == 1:
        os.remove('mi_rogues.txt')

    fileexists = os.path.exists('mi_normplot.txt')
    if fileexists == 1:
        os.remove('mi_normplot.txt')

    fileexists = os.path.exists('mi_plot.txt')
    if fileexists == 1:
        os.remove('mi_plot.txt')

    fileexists = os.path.exists('fort.10')
    if fileexists == 1:
        os.remove('fort.10')

    fileexists = os.path.exists('COORDS')
    if fileexists == 1:
        os.remove('COORDS')

    fileexists = os.path.exists('ROGUEPLOT')
    if fileexists == 1:
        os.remove('ROGUEPLOT')

    fileexists = os.path.exists('CORRELPLOT')
    if fileexists == 1:
        os.remove('CORRELPLOT')        

    ######################
    # Tail end processes #
    ######################

    # Transfer the final reflection and output files to defined space or leave in image directory

    if final_workdir != 'none' and final_workdir != image_dir:

        output_ref_destination = os.path.join(final_workdir,output_ref)
        output_log_destination = os.path.join(final_workdir,output_log)
        output_int_destination = os.path.join(final_workdir,output_integrate_log)

        fileexists = os.path.exists(output_ref_destination)
        if fileexists != 0:
            os.remove(output_ref_destination)

        fileexists = os.path.exists(output_log_destination)
        if fileexists != 0:
            os.remove(output_log_destination)

        fileexists = os.path.exists(output_int_destination)
        if fileexists != 0:
            os.remove(output_int_destination)            

        os.rename(output_ref,output_ref_destination)
        os.rename(output_log,output_log_destination)
        os.rename(output_integrate_log,output_int_destination)        

    else:

        output_ref_destination = os.path.join(image_dir,output_ref)
        output_log_destination = os.path.join(image_dir,output_log)
        output_int_destination = os.path.join(image_dir,output_integrate_log)        

    # Log and clean-up

    runtime = time.ctime(time.time())

    print 'Date:',runtime
    print '\nIntegrated and merged intensity file:',output_ref_destination
    print 'Integration log file file:',output_int_destination
    print 'Merging statistics log file:',output_log_destination

    time.sleep(4)
    return 0

if __name__ == "__main__":
    sys.exit(Run())


