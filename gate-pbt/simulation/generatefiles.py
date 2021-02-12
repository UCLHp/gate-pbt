# -*- coding: utf-8 -*-
"""
Created on Wed Dec 11 15:59:37 2019
@author: SCOURT01

Script to generate a Gate mac file plus a plan description and
source descrition file *for each field*. 

Currently no cropping and no rangeshifter implemented

"""
import os
import pydicom
import numpy as np
from math import radians, degrees, sqrt, isclose

import itk

import descriptionfiles as gfdf
import rangeshifter
import fieldstats
import jobsplitter
import config
import slurm


def rnd( num ):
    return round( num, 3 )


def rotation_matrix_x( deg ):
    """Return X rotation matrix for some angle in degrees"""
    x_rot_matrix = np.array([ [1.0, 0, 0], 
                              [0, np.cos(radians(deg)), -np.sin(radians(deg))], 
                              [0, np.sin(radians(deg)), np.cos(radians(deg))]
                           ])
    return x_rot_matrix 


def rotation_matrix_y( deg ):
    """Return Y rotation matrix for inout degrees  
    **Couch kicks are -deg about this axis
    """
    y_rot_matrix = np.array([ [np.cos(radians(deg)), 0, np.sin(radians(deg))], 
                              [0, 1.0, 0], 
                              [-np.sin(radians(deg)), 0, np.cos(radians(deg))]
                           ])
    return y_rot_matrix 


def rotation_matrix_z( deg ):
    """Return Z rotation matrix for input degrees"""
    z_rot_matrix = np.array([ [np.cos(radians(deg)), -np.sin(radians(deg)), 0], 
                              [np.sin(radians(deg)), np.cos(radians(deg)), 0], 
                              [0, 0, 1]
                           ])
    return z_rot_matrix


def get_rotation_matrix(ct_files, field):
    """Return combined matrix for patient setup and couchkick rotations"""
 
    img_props = get_img_properties( ct_files )
    
    # Setup as HFS, HFP, FFS etc...
    patient_position = img_props["PatientPosition"]
    
    # Find rotation matrix for patient set-up
    # Offset all by 0.001 to prevent a symmetric matrix.
    rot_matrix = None    
    if patient_position=="HFS":
        rot_matrix = rotation_matrix_y(0.0001)
    elif patient_position=="HFP":
        rot_matrix = rotation_matrix_z(180.0001)
    elif patient_position=="FFS":
        rot_matrix = rotation_matrix_y(180.0001)
    elif patient_position=="FFP":
        rot_matrix = np.dot(rotation_matrix_z(180.001),rotation_matrix_y(180.001))
    else:
        print("UNSUPPORTED PATIENT SETUP: {} in get_rotation_matrix".format(patient_position))
        exit(0)
                
    # Add couch kick to this
    couchkick = field.IonControlPointSequence[0].PatientSupportAngle 
    couch_rot = rotation_matrix_y( -couchkick )        

    total_rotation = np.dot( couch_rot, rot_matrix )  # Order matters 
        
    return total_rotation




# THIS WILL NOT WORK IF ROTATION MATRIX IS SYMMETRIC!!
def get_rotation_axis( rotation_matrix ):
    """Single axis for composite rotation"""
    # See https://en.wikipedia.org/wiki/Rotation_matrix
    paral_v = np.array([ rotation_matrix[2][1]-rotation_matrix[1][2],
                         rotation_matrix[0][2]-rotation_matrix[2][0],
                         rotation_matrix[1][0]-rotation_matrix[0][1]
                      ])
    norm = sqrt( np.dot( paral_v, paral_v ) )
    print("  rotation axis={}".format( paral_v/norm) )
    return paral_v / norm

    

def get_rotation_angle( rotation_matrix ):
    # TODO: This is magnitude of rotation... 
    #   will it always be in correct direction for our matrices?
    """Angle of composite rotations"""
    #https://en.wikipedia.org/wiki/Rotation_matrix
    trace = rotation_matrix[0][0]+rotation_matrix[1][1]+rotation_matrix[2][2]    
    angle = degrees( np.arccos( (trace-1.0)/2.0  ) )
    print("  (trace-1)/2={}".format( (trace-1.0)/2.0) )
    print("  rotation angle={}".format(angle) )
    return angle 



'''def get_rotation_angle_OLDZZZZZ( rotation_matrix ):
    """Angle of composite rotations"""
    #https://en.wikipedia.org/wiki/Rotation_matrix
    paral_v = np.array([ rotation_matrix[2][1]-rotation_matrix[1][2],
                         rotation_matrix[0][2]-rotation_matrix[2][0],
                         rotation_matrix[1][0]-rotation_matrix[0][1]
                      ])
    norm = sqrt( np.dot( paral_v, paral_v ) )
    
    angle = degrees( np.arcsin( norm/2.0 ) )
    return angle'''  
    ## This method will fail if rotation matrix is symmetric



def get_translation_vector( ct_files, field, rotation_matrix ):
    """Return the translation vector required to shift plan isocentre
    to origin of World volume (to be applied AFTER couch rotation)
    """
    
    img_props = get_img_properties( ct_files )
    
    minCornerVox = np.array( img_props["MinCornerVoxelCentre"] ) 
    voxelDims_mm = np.array( [img_props["PixelSpacing_x"],img_props["PixelSpacing_y"],img_props["SliceThickness"]  ] )
    imgDims_pixels = np.array( [img_props["Columns"],img_props["Rows"],img_props["Slices"]]  ) 
    # rows and columns correct way round?
    
    print("  minCornerVox={}".format(minCornerVox))
    print("  voxelDims_mm={}".format(voxelDims_mm))
    print("  imgDims_pixels={}".format(imgDims_pixels))

    #Centre of 3D CT image in patient coords
    imgCenter = minCornerVox - 0.5*voxelDims_mm + 0.5*imgDims_pixels*voxelDims_mm
    
    print("  imgCenter={}".format(imgCenter))

    dcmIso = np.array( field.IonControlPointSequence[0].IsocenterPosition )
    
    print("  dcmIso={}".format(dcmIso))
        
    #Translation required to position isocentre at World origin     
    trans_without_rot = imgCenter - dcmIso 
    
    print("  trans_without_rot={}".format(trans_without_rot))
    
    print("  rotation_matrix={}".format(rotation_matrix))
    
    #Rotated translation to account for PatientSupportAngle
    trans_after_rot = np.dot( rotation_matrix, trans_without_rot )
    
    print("  trans_after_rot={}".format(trans_after_rot))
    
    return trans_after_rot



def get_img_properties( ct_files ):
    """Method to retrieve Rows, Columns, pixelSpacing from DICOM image"""
    
    properties = {}
    
    #ct_files = [ f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir,f)) and "CT" in f  ]
    ## NOT GOOD; CHECK FILE TAGS
    ## CHECK ALL IMAGES BELONG TO SAME SEQUENCE
    
    #ds = pydicom.dcmread( os.path.join(input_dir,ct_files[0]) )
    ds = pydicom.dcmread( ct_files[0] )

    
    properties["Rows"] = ds.Rows
    properties["Columns"] = ds.Columns
    properties["Slices"] = len(ct_files) ## NO - TODO THIS PROPERLY!!!
    properties["PixelSpacing_x"] = ds.PixelSpacing[0]
    properties["PixelSpacing_y"] = ds.PixelSpacing[1]
    properties["SliceThickness"] = ds.SliceThickness
    ##properties["SliceThickness"] = 1.0

        
    properties["ImageOrientationPatient"] = ds.ImageOrientationPatient
    
    img_limits = corner_voxel_centres( ct_files, ds.ImageOrientationPatient )
    properties["MinCornerVoxelCentre"] = [ img_limits["minX"], img_limits["minY"], img_limits["minZ"]]
    
    # Patient setup ("HFS", "FFS" etc)
    properties["PatientPosition"] = ds.PatientPosition
    
    return properties
    


 ## TODO: appraoch may need rethink
def corner_voxel_centres( ct_files, imageorientationpatient ): 
    """X,Y,Z limits: centre of corner voxels
    """
    
    iop = imageorientationpatient
    
    xmin, xmax = 99999.0, -99999.0
    ymin, ymax = 99999.0, -99999.0
    zmin, zmax = 99999.0, -99999.0  
       
    for i,f in enumerate(ct_files):
        
        ds = pydicom.dcmread( f )
        
        #z = ds.SliceLocation
        z = ds.ImagePositionPatient[2]
        
        if z<zmin:
            zmin = z
        if z>zmax:
            zmax = z
            
        if i==0:
            #Only get x and y 1 time
            rows = ds.Rows
            cols = ds.Columns
            
            ## TODO: is this approach valid/robust?
            ## TODO could use ImageOrientation here?
            if ds.ImagePositionPatient[0]<0:  
                 xmin = ds.ImagePositionPatient[0]
                 xmax = xmin + cols * ds.PixelSpacing[0]
            else:
                 xmax = ds.ImagePositionPatient[0]         
                 xmin = xmax - (cols-1) * ds.PixelSpacing[0]
                 # cols-1 since we want centre of final voxel       
          
            if ds.ImagePositionPatient[1]<0:
                ymin = ds.ImagePositionPatient[1]
                ymax = ymin + rows * ds.PixelSpacing[1]
            else:
                ymax = ds.ImagePositionPatient[1]
                ymin = ymax - (rows-1) * ds.PixelSpacing[1]   
                # rows-1 since we want centre of final voxel
         
    dct = {"minX":xmin, "maxX":xmax, "minY":ymin, "maxY":ymax, "minZ":zmin, "maxZ":zmax }
    return dct



def get_dose_voxel_dims( dcm_dose ):
    """Returns x,y,z dims of dose grid from single DICOM dose file"""
    ds = pydicom.dcmread( dcm_dose )
    if not isclose(ds.PixelSpacing[0],ds.PixelSpacing[1]):
        print("Dose voxels not symmetric")   
    thickness = ds.GridFrameOffsetVector[1]-ds.GridFrameOffsetVector[0] # TODO: is this best way?
    return [ ds.PixelSpacing[0], ds.PixelSpacing[1], thickness]




def write_mac_file(template, output, planDescription, sourceDescription, 
                   setRotationAngle=None, setRotationAxis=None,
                   setTranslation=None,
                   setVoxelSize=None, setImage=None,
                   rangeshift_rot=None,
                   rangeshift_trans=None,
                   rangeshift_thick=None
                   ):
    """Write the main .mac file to be run in Gate
    Takes a template file and modifies appropriate lines"""
    #TODO: add setTotalNumberOfPrimaries
    #TODO: only edit fields provided, not "None"
    with open(output,'w') as out:
        for line in open( template, "r" ):
            
            if "/patient/placement/setRotationAngle" in line and setRotationAngle is not None:
                out.write( "/gate/patient/placement/setRotationAngle    {} deg\n".format( setRotationAngle  ) )
                
            elif "patient/placement/setRotationAxis" in line and setRotationAxis is not None:
                out.write( "/gate/patient/placement/setRotationAxis    {} {} {}\n".format(
                    setRotationAxis[0],setRotationAxis[1],setRotationAxis[2]) 
                    )
            
            elif "/patient/placement/setTranslation" in line and setTranslation is not None:
                out.write( "/gate/patient/placement/setTranslation    {} {} {} mm\n".format(
                        setTranslation[0],setTranslation[1],setTranslation[2] )
                         )
            
            elif "setPlan" in line and planDescription is not None:
                out.write( "/gate/source/PBS/setPlan    {{path}}/data/{}\n".format(planDescription) )
            
            elif "setSourceDescriptionFile" in line and sourceDescription is not None:
                out.write( "/gate/source/PBS/setSourceDescriptionFile    {{path}}/data/{}\n".format(sourceDescription) )
            
            elif "dose3d/setVoxelSize" in line and setVoxelSize is not None:
                out.write( "/gate/actor/dose3d/setVoxelSize    {} {} {} mm\n".format(
                    setVoxelSize[0],setVoxelSize[1],setVoxelSize[2] ) 
                    )
            
            elif "let3d/setVoxelSize" in line and setVoxelSize is not None:    
                toprint = "/gate/actor/let3d/setVoxelSize    {} {} {} mm\n".format(
                          setVoxelSize[0],setVoxelSize[1],setVoxelSize[2] 
                          )
                if line[0]=="#":
                    out.write( "#"+toprint)
                else:
                    out.write(toprint)
                
            
            elif "patient/geometry/setImage" in line and setImage is not None:
                out.write( "/gate/patient/geometry/setImage    {{path}}/data/{}\n".format(setImage) )    
                
            elif  "rangeshifter/placement/setRotationAngle" in line and rangeshift_rot is not None:
                out.write( "/gate/rangeshifter/placement/setRotationAngle    {} deg\n".format(rangeshift_rot) )
                
            elif "rangeshifter/placement/setTranslation" in line and rangeshift_trans is not None:
                out.write( "/gate/rangeshifter/placement/setTranslation    {} {} {} mm\n".format(
                    rangeshift_trans[0],rangeshift_trans[1],rangeshift_trans[2]) 
                    )
            elif "rangeshifter/geometry/setYLength" in line and rangeshift_thick is not None:
                out.write("/gate/rangeshifter/geometry/setYLength    {} mm\n".format(rangeshift_thick) )
                
                
            else:
                out.write(line)



def field_has_rangeshifter( field ):
    """Return true if field has rangeshifter"""
    return hasattr(field.IonControlPointSequence[0],"RangeShifterSettingsSequence")


def get_source_offset(field, rs):
    """Offset source to allow rangeshifter in beam path"""
    source_offset = 0
    if field_has_rangeshifter(field):
        # offset source by thickness, rangeshifter offset from nozzle exit
        # and some arbitrary distance so source is not in rangeshifter
        #####source_offset = rs.thickness + rs.offset + 5  
        rsss = field.IonControlPointSequence[0].RangeShifterSettingsSequence[0]
        snout_pos = field.IonControlPointSequence[0].SnoutPosition
        rs_inset = rsss.IsocenterToRangeShifterDistance - snout_pos
        source_offset = rs_inset + rs.thickness + 5
        print("source_offset = {}".format(source_offset))
    return source_offset



def calc_dose_offset( mhdimgpath, dcmdose ):
    """ Calculate correct mhd Offset (ITK Origin) for Gate's dose output
    
    A bug in Gate means that this can be wrong for certain non-HFS 
    patirn positions so we must correct it manually in the ouput files
    """
    dose_vox_dims = np.array(  get_dose_voxel_dims( dcmdose )  )
    
    mhdimg = itk.imread( mhdimgpath )
    ctorigin = np.array(  mhdimg.GetOrigin()  )
    img_vox_dims = np.array(  mhdimg.GetSpacing()  )
    direction = np.array(  mhdimg.GetDirection()*[1,1,1]  )
    
    doseorigin = ctorigin - 0.5*direction*img_vox_dims + 0.5*direction*dose_vox_dims
    
    return doseorigin
    
    
    
    




## TODO: THIS METHOD SHOULD BE FIELD SPECIFIC AS IN FUTURE WE MIGHT HAVE DIFFERENT IMAGES
##    FOR EACH FIELD, CROPPED FOR MINIMUM MEMORY USAGE
    
def generate_files(ct_files, plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, ct_mhd, sim_dir):
    """Method to generate all description and mac files"""
    
    # TODO: assumes all dose files are same plan; write check
    #dose_vox_dims = get_dose_voxel_dims( os.path.join(dcm_data_dir,dose_files[0])  ) 
    dose_vox_dims = get_dose_voxel_dims(dose_files[0]) 

    #dcmPlan = pydicom.dcmread(  os.path.join(dcm_data_dir,plan_file)  )
    dcmPlan = pydicom.dcmread( plan_file )
    
    # Dictionary of field name and number of primaries required
    req_prims = fieldstats.get_required_primaries( dcmPlan )
    print("Required primaries = ",  req_prims )
    # Update simconfig.ini file
    config.add_prims_to_config( CONFIG, req_prims )

        
    for field in dcmPlan.IonBeamSequence:   
        
        beamname = str(field.BeamName).replace(" ","")
        
        # Add beam ref number to config file
        beam_ref_no = field.BeamNumber
        config.add_beam_ref_no( CONFIG, beamname, beam_ref_no )
        
        # Calculate correct origin for dose output
        # TODO: THIS MAY BE FIELD SPECIFIC IF WE DO ANYTHING CLEVER WITH
        #   IMAGE CROPPING.
        dose_origin = calc_dose_offset( os.path.join(sim_dir,"data",ct_mhd), dose_files[0] )
        config.add_correct_dose_offset(CONFIG, beamname, dose_origin)
        
        # Rangeshifter object
        rs = rangeshifter.get_props( field )  
        
        # Offset to source positon (snout position) needed to allow rangeshifter
        source_offset = get_source_offset(field, rs)
        
        
        ##### Make field-specific PlanDescriptionFile
        fld_dsc = gfdf.get_field_description(field)
        plan_dsc = gfdf.get_plan_description(dcmPlan, field)   
        pdf_filename = "PlanDescFile_"+beamname+".txt"
        gfdf.make_field_description( os.path.join(sim_dir,"data",pdf_filename),
                                    plan_dsc, fld_dsc 
                                    )
        
        
        ##### Make field-specific SourceDescriptionFile
        snout_pos = field.IonControlPointSequence[0].SnoutPosition + source_offset 
        sdf_filename = "SourceDescFile_"+beamname+".txt"
        gfdf.make_source_description(TEMPLATE_SOURCE, 
                                     os.path.join(sim_dir,"data",sdf_filename), snout_pos
                                     )
        
        
        ##### Make field-specific .mac Gate file for simulation    
        rotation_matrix = get_rotation_matrix(ct_files, field)
        axis = get_rotation_axis(rotation_matrix)
        angle = get_rotation_angle(rotation_matrix)
        translation_vector = get_translation_vector( ct_files, field, rotation_matrix )
        #print( translation_vector )
        mac_filename = os.path.join(sim_dir,"mac",beamname+".mac")
        write_mac_file(TEMPLATE_MAC, mac_filename, pdf_filename, sdf_filename,
                       # setRotationAngle=-field.IonControlPointSequence[0].PatientSupportAngle,
                       setRotationAngle=angle,
                       setRotationAxis=axis,
                       setTranslation=translation_vector,
                       setVoxelSize=dose_vox_dims,
                       setImage=ct_mhd,
                       rangeshift_rot=rs.rotation,
                       rangeshift_trans=rs.translation,
                       rangeshift_thick=rs.thickness
                      )
 
    
        ##### Potentially split field mac file here ####
        # TODO
        # Simulate Nreq/1000 for reasonable stats

        splits = 10  ## TODO automate this for efficiency
        nprotons = int( req_prims[field.BeamName]/1000 )  # will be split into separate sims
        #splits = 80
        #nprotons = 80000
        
        jobsplitter.split_by_primaries( mac_filename, primaries=nprotons, splits=splits)
        
        
        # Make SLURM job script
        scriptname = "submit_"+beamname+".sh"
        scriptpath = os.path.join(sim_dir, scriptname )
        slurm.make_script(sim_dir, beamname, splits, scriptpath)











'''
def main():
   
    TEMPLATE_SOURCE = "TEMPLATE_SourceDescFile.txt"
    TEMPLATE_MAC = "TEMPLATE_simulateField.txt"
    
    dcm_data_dir = "zzzPaedCranio02_data"
    
    #Check all images belong to same image and that only one plan and one structure set are present
    ct_files, plan_file, dose_files = search_dcm_dir( dcm_data_dir )
    
    # TODO: assumes all dose files are same plan; write check
    dose_vox_dims = get_dose_voxel_dims( os.path.join(dcm_data_dir,dose_files[0])  ) 
    
    dcmPlan = pydicom.dcmread(  os.path.join(dcm_data_dir,plan_file)  )
        
    for field in dcmPlan.IonBeamSequence:       
        beamname = str(field.BeamName).replace(" ","")
        
        #Make field-specific PlanDescriptionFile
        fld_dsc = gfdf.get_field_description(field)
        plan_dsc = gfdf.get_plan_description(dcmPlan, field)   
        pdf_filename = "PlanDescFile_"+beamname+".txt"
        gfdf.make_field_description( pdf_filename, plan_dsc, fld_dsc  )
        
        #Make field-specific SourceDescriptionFile
        snout_pos = field.IonControlPointSequence[0].SnoutPosition
        sdf_filename = "SourceDescFile_"+beamname+".txt"
        gfdf.make_source_description(TEMPLATE_SOURCE, sdf_filename, snout_pos)
        
        #Make field-specific .mac Gate file for simulation    
        translation_vector = get_translation_vector( ct_files, field )
        #print( translation_vector )
        mac_filename = beamname+".mac"
        write_mac_file(TEMPLATE_MAC, mac_filename, pdf_filename, sdf_filename,
                       setRotationAngle=-field.IonControlPointSequence[0].PatientSupportAngle,
                       setTranslation=translation_vector,
                       setVoxelSize=dose_vox_dims
                      )
    
    #if not os.path.isdir('/simulationFiles'):
    #    os.mkdir('/simulationFiles')


if __name__=="__main__":
    main()
'''  