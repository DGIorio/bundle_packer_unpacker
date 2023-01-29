import sys
import os
import struct
import zlib
import binascii
import tempfile
import math
#import shutil


version = "3.2.0"
date = "2023-Jan-15"


def unpack_multiple_bundles(bundle_dir, main_save_directory, game, unpack_to_same_folder=False):
	#wrong_ones = 0
	#right_ones = 0
	for file in os.listdir(bundle_dir):
		bundle_path = os.path.join(bundle_dir, file)
		if not os.path.isfile(bundle_path):
			continue
		print("Unpacking %s" % file)
		ids_table_name = "IDs_" + file
		if unpack_to_same_folder:
			save_directory = main_save_directory
		else:
			save_directory = os.path.join(main_save_directory, file.split(".")[0])
		
		if game.lower() == "bp":
			status = unpack_bundle(bundle_path, save_directory, ids_table_name)
		elif game.lower() == "mw":
			status = unpack_bundle_mw(bundle_path, save_directory, ids_table_name)
		
		if status == 1:
			continue
		
		# ids_path = os.path.join(save_directory, ids_table_name)
		# if os.path.isfile(ids_path):
			# pack_bundle(ids_path, save_directory, "out" + file)
			# #pack_bundle_mw(ids_path, save_directory, "out" + file)
			
			# output_path = os.path.join(save_directory, "out" + file)
			
			# with open(bundle_path, "rb") as f, open(output_path, "rb") as g:
				# bundle_data = f.read()
				# out_bundle_data = g.read()
			# if bundle_data != out_bundle_data:
				# print("Packed file %s is different from the original." %file)
				# wrong_ones += 1
			# else:
				# right_ones += 1
		
		# shutil.rmtree(save_directory)
	
	#print("%d files packed correclty" %right_ones)
	#print("%d files packed incorreclty" %wrong_ones)
	
	return 0


def pack_multiple_bundles(bundle_dir, save_directory):
	for file in os.listdir(bundle_dir):
		ids_path = os.path.join(bundle_dir, file)
		if not os.path.isfile(ids_path):
			continue
		print("Packing %s" % file)
		status = pack_bundle(ids_path, save_directory, "out" + file)
	
	return 0


def unpack_bundle(bundle_path, save_directory, ids_table_name="IDs.BIN"):
	with open(bundle_path, "rb") as f:
		try:
			macMagicNumber = str(f.read(0x4), 'ascii')
		except:
			print("Error: not a valid bundle. Magic number (bnd2 or bndl) is incorrect.")
			return 1
		if macMagicNumber != 'bnd2' and macMagicNumber != 'bndl':
			print("Error: not a valid bundle. Magic number (bnd2 or bndl) is incorrect.")
			return 1
		
		if macMagicNumber == 'bnd2':
			f.seek(0x8, 0)
			muPlatform = f.read(0x4)
			muPlatform_little_endian = struct.unpack("<I", muPlatform)[0]
			muPlatform_big_endian = struct.unpack(">I", muPlatform)[0]
			f.seek(0x4, 0)
			
			if muPlatform_little_endian == 0x1:
				print("Info: bundle platform is PC or PS4.")
				endian = "<"
			elif muPlatform_big_endian == 0x2:
				print("Info: bundle platform is X360.")
				endian = ">"
			elif muPlatform_big_endian == 0x3:
				print("Info: bundle platform is PS3.")
				endian = ">"
			else:
				print("Error: bundle platform not supported yet. Select a PC, PS3, PS4 or X360 file version.")
				return 1
		elif macMagicNumber == 'bndl':
			f.seek(0x58, 0)
			muPlatform = f.read(0x4)
			muPlatform_little_endian = struct.unpack("<I", muPlatform)[0]
			muPlatform_big_endian = struct.unpack(">I", muPlatform)[0]
			f.seek(0x4, 0)
			
			if muPlatform_little_endian == 0x1:
				print("Info: bundle platform is B5 PC.")
				endian = "<"
			elif muPlatform_big_endian == 0x2:
				print("Info: bundle platform is B5 X360.")
				endian = ">"
			elif muPlatform_big_endian == 0x3:
				print("Info: bundle platform is B5 PS3.")
				endian = ">"
			else:
				print("Error: bundle platform not supported yet. Select a PC, PS3, PS4 or X360 file version.")
				return 1
			
			status = unpack_bundle_bndl(f, save_directory, ids_table_name=ids_table_name, endian=endian)
			return status
		
		muVersion = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muPlatform = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muDebugDataOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muResourceEntriesCount = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muResourceEntriesOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
		mauResourceDataOffset = struct.unpack("%s3I" % endian, f.read(0xC))
		muFlags = struct.unpack("%sI" % endian, f.read(0x4))[0]
		padding = f.read(0x8)
		
		if os.path.getsize(bundle_path) < mauResourceDataOffset[-1]:
			print("Error: bundle might not have resource data or its header is incorrect.")
			return 1
		
		debug_data = f.read(muResourceEntriesOffset - f.tell())
		resource_entries_data = f.read(mauResourceDataOffset[0] - f.tell())
		
		for i in range(0, muResourceEntriesCount):
			f.seek(muResourceEntriesOffset + i*0x40, 0)
			if endian == "<":
				mResourceId = bytes_to_id(f.read(0x4))
				_ = f.read(0x4)
				muImportHash = bytes_to_id(f.read(0x4))
				_ = f.read(0x4)
			else:
				_ = f.read(0x4)
				mResourceId = bytes_to_id(f.read(0x4))
				_ = f.read(0x4)
				muImportHash = bytes_to_id(f.read(0x4))
			mauUncompressedSizeAndAlignment = struct.unpack("%s3I" % endian, f.read(0xC))
			mauSizeAndAlignmentOnDisk = struct.unpack("%s3I" % endian, f.read(0xC))
			mauDiskOffset = struct.unpack("%s3I" % endian, f.read(0xC))
			muImportOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
			muResourceTypeId = struct.unpack("%sI" % endian, f.read(0x4))[0]
			muImportCount = struct.unpack("%sH" % endian, f.read(0x2))[0]
			unused_muFlags = struct.unpack("%sB" % endian, f.read(0x1))[0]
			unused_muStreamIndex = struct.unpack("%sB" % endian, f.read(0x1))[0]
			
			muResourceType, nibbles = get_resourcetype_nibble(muResourceTypeId)
			
			resource_dir = os.path.join(save_directory, muResourceType)
			os.makedirs(resource_dir, exist_ok = True)
			
			for j in range(0, 3):
				if mauUncompressedSizeAndAlignment[j] == 0:
					continue
				f.seek(mauResourceDataOffset[j] + mauDiskOffset[j], 0)
				resource_data = f.read(mauSizeAndAlignmentOnDisk[j])
				
				if muFlags == 0x7 or muFlags == 0xF:
					zobj = zlib.decompressobj()
					if endian == "<":
						try:
							resource_data = zobj.decompress(resource_data, mauUncompressedSizeAndAlignment[j] - nibbles[j])
						except:
							resource_data = zobj.decompress(resource_data)
					else:
						resource_data = zobj.decompress(resource_data)
				
				resource_path = os.path.join(resource_dir, mResourceId + ".dat")
				if j == 1 and (muPlatform_little_endian == 0x1 or muPlatform_big_endian == 0x2):
					if muResourceType == "Raster":
						resource_path = os.path.join(resource_dir, mResourceId + "_texture.dat")
					elif muResourceType == "Renderable":
						resource_path = os.path.join(resource_dir, mResourceId + "_model.dat")
					elif muResourceType == "VFXMeshCollection":
						resource_path = os.path.join(resource_dir, mResourceId + "_model.dat")
					elif muResourceType == "ShaderProgramBuffer":
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
					else:
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				elif j == 2 and muPlatform_big_endian == 0x3:
					if muResourceType == "Raster":
						resource_path = os.path.join(resource_dir, mResourceId + "_texture.dat")
					elif muResourceType == "Renderable":
						resource_path = os.path.join(resource_dir, mResourceId + "_model.dat")
					elif muResourceType == "VFXMeshCollection":
						resource_path = os.path.join(resource_dir, mResourceId + "_model.dat")
					elif muResourceType == "ShaderProgramBuffer":
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
					else:
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				elif j == 1:
					resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				elif j == 2:
					resource_path = os.path.join(resource_dir, mResourceId + "_unknown2.dat")
				
				with open(resource_path, "wb") as g:
					g.write(resource_data)
	
	ids_path = os.path.join(save_directory, ids_table_name)
	with open(ids_path, "wb") as f:
		f.write(macMagicNumber.encode('utf-8'))
		f.write(struct.pack("%sI" % endian, muVersion))
		f.write(struct.pack("%sI" % endian, muPlatform))
		f.write(struct.pack("%sI" % endian, muDebugDataOffset))
		f.write(struct.pack("%sI" % endian, muResourceEntriesCount))
		f.write(struct.pack("%sI" % endian, muResourceEntriesOffset))
		f.write(struct.pack("%s3I" % endian, *mauResourceDataOffset))
		f.write(struct.pack("%sI" % endian, muFlags))
		f.seek(0x8, 1)
		f.write(debug_data)
		f.write(resource_entries_data)
	
	return 0


def unpack_bundle_mw(bundle_path, save_directory, ids_table_name="IDs.BIN"):
	with open(bundle_path, "rb") as f:
		try:
			macMagicNumber = str(f.read(0x4), 'ascii')
		except:
			print("Error: not a valid bundle. Magic number (bnd2 or bndl) is incorrect.")
			return 1
		if macMagicNumber != 'bnd2' and macMagicNumber != 'bndl':
			print("Error: not a valid bundle. Magic number (bnd2 or bndl) is incorrect.")
			return 1
		
		data_type = ["H", 0x2]
		numDataOffsets = 4
		
		if macMagicNumber == 'bnd2':
			f.seek(0x4 + data_type[1], 0)
			muPlatform = f.read(data_type[1])
			muPlatform_little_endian = struct.unpack("<%s" % data_type[0], muPlatform)[0]
			muPlatform_big_endian = struct.unpack(">%s" % data_type[0], muPlatform)[0]
			f.seek(0x4, 0)
			
			if muPlatform_little_endian == 0x1:
				print("Info: bundle platform is PC or PS4.")
				endian = "<"
			elif muPlatform_big_endian == 0x2:
				print("Info: bundle platform is PS3.")
				endian = ">"
			elif muPlatform_big_endian == 0x3:
				print("Info: bundle platform is X360.")
				endian = ">"
			else:
				print("Error: bundle platform not supported yet. Select a PC, PS3, PS4 or X360 file version.")
				return 1
		elif macMagicNumber == 'bndl':
			f.seek(0x58, 0)
			muPlatform = f.read(0x4)
			muPlatform_little_endian = struct.unpack("<I", muPlatform)[0]
			muPlatform_big_endian = struct.unpack(">I", muPlatform)[0]
			f.seek(0x4, 0)
			
			if muPlatform_little_endian == 0x1:
				print("Info: bundle platform is B5 PC.")
				endian = "<"
			elif muPlatform_big_endian == 0x2:
				print("Info: bundle platform is B5 X360.")
				endian = ">"
			elif muPlatform_big_endian == 0x3:
				print("Info: bundle platform is B5 PS3.")
				endian = ">"
			else:
				print("Error: bundle platform not supported yet. Select a PC, PS3, PS4 or X360 file version.")
				return 1
			
			status = unpack_bundle_bndl(f, save_directory, ids_table_name=ids_table_name, endian=endian)
			return status
		
		muVersion = struct.unpack("%s%s" % (endian, data_type[0]), f.read(data_type[1]))[0]
		muPlatform = struct.unpack("%s%s" % (endian, data_type[0]), f.read(data_type[1]))[0]
		muDebugDataOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muResourceEntriesCount = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muResourceEntriesOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
		mauResourceDataOffset = struct.unpack("%s%dI" % (endian, numDataOffsets), f.read(numDataOffsets*0x4))
		muFlags = struct.unpack("%sI" % endian, f.read(0x4))[0]
		pad1 = struct.unpack("%sI" % endian, f.read(0x4))[0]
		pad2 = struct.unpack("%sI" % endian, f.read(0x4))[0]
		
		if os.path.getsize(bundle_path) < mauResourceDataOffset[-1]:
			print("Error: bundle might not have resource data or its header is incorrect.")
			return 1
		
		debug_data = f.read(muResourceEntriesOffset - f.tell())
		resource_entries_data = f.read(mauResourceDataOffset[0] - f.tell())
		
		for i in range(0, muResourceEntriesCount):
			f.seek(muResourceEntriesOffset + i*0x48, 0)
			if endian == "<":
				mResourceId = bytes_to_id(f.read(0x4))
				countBlock, _ = struct.unpack("%s2B" % endian, f.read(0x2))
				count, _ = struct.unpack("%s2B" % endian, f.read(0x2))
			else:
				_, countBlock = struct.unpack("%s2B" % endian, f.read(0x2))
				_, count = struct.unpack("%s2B" % endian, f.read(0x2))
				mResourceId = bytes_to_id(f.read(0x4))
			mauUncompressedSizeAndAlignment = struct.unpack("%s%dI" % (endian, numDataOffsets), f.read(numDataOffsets*0x4))
			mauSizeAndAlignmentOnDisk = struct.unpack("%s%dI" % (endian, numDataOffsets), f.read(numDataOffsets*0x4))
			mauDiskOffset = struct.unpack("%s%dI" % (endian, numDataOffsets), f.read(numDataOffsets*0x4))
			muImportOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
			muResourceTypeId = struct.unpack("%sI" % endian, f.read(0x4))[0]
			muImportCount = struct.unpack("%sH" % endian, f.read(0x2))[0]
			unused_muFlags = struct.unpack("%sB" % endian, f.read(0x1))[0]
			muStreamIndex = struct.unpack("%sB" % endian, f.read(0x1))[0]
			
			muResourceType, nibbles = get_resourcetype_nibble_mw(muResourceTypeId)
			
			if countBlock != 0:
				mResourceId += "_" + str(countBlock) 
				if count != 0:
					mResourceId += "_" + str(count)
			elif countBlock == 0 and count != 0:
				mResourceId += "_" + str(countBlock)
				mResourceId += "_" + str(count)
			
			resource_dir = os.path.join(save_directory, muResourceType)
			os.makedirs(resource_dir, exist_ok = True)
			
			for j in range(0, numDataOffsets):
				if mauUncompressedSizeAndAlignment[j] == 0:
					continue
				f.seek(mauResourceDataOffset[j] + mauDiskOffset[j], 0)
				resource_data = f.read(mauSizeAndAlignmentOnDisk[j])
				
				if muPlatform_little_endian == 0x1 and (muFlags == 0x1 or muFlags == 0x5 or muFlags == 0x9 or muFlags == 0x21 or muFlags == 0x29):
					zobj = zlib.decompressobj()
					if endian == "<":
						try:
							resource_data = zobj.decompress(resource_data, mauUncompressedSizeAndAlignment[j] - nibbles[j])
						except:
							resource_data = zobj.decompress(resource_data)
					else:
						resource_data = zobj.decompress(resource_data)
				
				elif muPlatform_big_endian == 0x2 and (muFlags == 0x3 or muFlags == 0x7 or muFlags == 0xB or muFlags == 0x123):
					zobj = zlib.decompressobj()
					if endian == "<":	#not using
						try:
							resource_data = zobj.decompress(resource_data, mauUncompressedSizeAndAlignment[j] - nibbles[j])
						except:
							resource_data = zobj.decompress(resource_data)
					else:
						resource_data = zobj.decompress(resource_data)
				
				elif muPlatform_big_endian == 0x3 and (muFlags == 0x1 or muFlags == 0x7 or muFlags == 0x11 or muFlags == 0x21 or muFlags == 0x27):
					zobj = zlib.decompressobj()
					if endian == "<":	#not using
						try:
							resource_data = zobj.decompress(resource_data, mauUncompressedSizeAndAlignment[j] - nibbles[j])
						except:
							resource_data = zobj.decompress(resource_data)
					else:
						resource_data = zobj.decompress(resource_data)
				
				resource_path = os.path.join(resource_dir, mResourceId + ".dat")
				if j == 1 and (muPlatform_little_endian == 0x1 or muPlatform_big_endian == 0x3):
					if muResourceType == "Raster" or muResourceType == "Texture":
						resource_path = os.path.join(resource_dir, mResourceId + "_texture.dat")
					elif muResourceType == "Renderable":
						resource_path = os.path.join(resource_dir, mResourceId + "_model.dat")
					else:
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				elif j == 1 and muPlatform_little_endian == 0x2:
					if muResourceType == "Raster" or muResourceType == "Texture":
						resource_path = os.path.join(resource_dir, mResourceId + "_texture1.dat")
					elif muResourceType == "Renderable":
						resource_path = os.path.join(resource_dir, mResourceId + "_indices.dat")
					else:
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				elif j == 2 and muPlatform_big_endian == 0x2:
					if muResourceType == "Raster" or muResourceType == "Texture":
						resource_path = os.path.join(resource_dir, mResourceId + "_texture.dat")
					elif muResourceType == "Renderable":
						#resource_path = os.path.join(resource_dir, mResourceId + "_model.dat")
						resource_path = os.path.join(resource_dir, mResourceId + "_vertices.dat")
					else:
						resource_path = os.path.join(resource_dir, mResourceId + "_unknown2.dat")
				elif j == 1:
					resource_path = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				elif j == 2:
					resource_path = os.path.join(resource_dir, mResourceId + "_unknown2.dat")
				elif j == 3:
					resource_path = os.path.join(resource_dir, mResourceId + "_unknown3.dat")
				
				with open(resource_path, "wb") as g:
					g.write(resource_data)
	
	ids_path = os.path.join(save_directory, ids_table_name)
	with open(ids_path, "wb") as f:
		f.write(macMagicNumber.encode('utf-8'))
		f.write(struct.pack("%s%s" % (endian, data_type[0]), muVersion))
		f.write(struct.pack("%s%s" % (endian, data_type[0]), muPlatform))
		f.write(struct.pack("%sI" % endian, muDebugDataOffset))
		f.write(struct.pack("%sI" % endian, muResourceEntriesCount))
		f.write(struct.pack("%sI" % endian, muResourceEntriesOffset))
		f.write(struct.pack("%s%dI" % (endian, numDataOffsets), *mauResourceDataOffset))
		f.write(struct.pack("%sI" % endian, muFlags))
		f.write(struct.pack("%sI" % endian, pad1))
		f.write(struct.pack("%sI" % endian, pad2))
		f.write(debug_data)
		f.write(resource_entries_data)
	
	return 0


def pack_bundle(resource_entries_path, output_directory, output_name):
	directory_path = os.path.dirname(resource_entries_path)
	output_path = os.path.join(output_directory, output_name)
	len_resource_entries_data = os.path.getsize(resource_entries_path)
	
	with open(resource_entries_path, "rb") as f:
		try:
			macMagicNumber = str(f.read(0x4), 'ascii')
		except:
			print("Error: not a valid bundle. Magic number (bnd2) is incorrect.")
			return 1
		if macMagicNumber != 'bnd2':
			print("Error: not a valid bundle. Magic number (bnd2) is incorrect.")
			return 1
		
		muVersion = struct.unpack("<I", f.read(0x4))[0]
		muPlatform = struct.unpack("<I", f.read(0x4))[0]
		if muPlatform != 0x1:
			print("Error: bundle platform not supported yet. Select a PC file version.")
			return 1
		
		muDebugDataOffset = struct.unpack("<I", f.read(0x4))[0]
		muResourceEntriesCount = struct.unpack("<I", f.read(0x4))[0]
		muResourceEntriesOffset = struct.unpack("<I", f.read(0x4))[0]
		mauResourceDataOffset = struct.unpack("<3I", f.read(0xC))
		muFlags = struct.unpack("<I", f.read(0x4))[0]
		padding = f.read(0x8)
		
		muResourceEntriesCount_verification = (len_resource_entries_data - muResourceEntriesOffset)//0x40
		if muResourceEntriesCount != muResourceEntriesCount_verification:
			print("Warning: muResourceEntriesCount does not match the number of resource entries. It will be used %d" % muResourceEntriesCount_verification)
			muResourceEntriesCount = muResourceEntriesCount_verification
		
		debug_data = f.read(muResourceEntriesOffset - f.tell())
		
		mResources = []
		for i in range(0, muResourceEntriesCount):
			f.seek(muResourceEntriesOffset + i*0x40, 0)
			mResourceId = bytes_to_id(f.read(0x4))
			f.seek(0x34, 1)
			muResourceTypeId = struct.unpack("<I", f.read(0x4))[0]
			
			muResourceType, nibbles = get_resourcetype_nibble(muResourceTypeId)
			
			resource_dir = os.path.join(directory_path, muResourceType)
			resource_path = os.path.join(resource_dir, mResourceId + ".dat")
			if not os.path.isfile(resource_path):
				resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + ".dat")
				if not os.path.isfile(resource_path_alternative):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + ".dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + ".dat")
						if not os.path.isfile(resource_path_alternative):
							print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + ".dat", resource_path))
							return 1
				resource_path = resource_path_alternative
			
			resource_path_body = ""
			if muResourceType == "Raster":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_texture.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_texture.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_texture.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_texture.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_texture.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			elif muResourceType == "Renderable":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_model.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_model.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_model.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_model.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_model.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			elif muResourceType == "VFXMeshCollection":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_model.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_model.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_model.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_model.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_model.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			elif muResourceType == "ShaderProgramBuffer":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_unknown.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_unknown.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_unknown.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_unknown.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			
			mResources.append([mResourceId, muResourceType, nibbles, resource_path, resource_path_body])
	
	resources_data = b''
	resources_data_body = b''
	resources_data2 = b''
	
	mauUncompressedSizes = []
	mauSizesOnDisk = []
	mauDiskOffsets = []
	
	for mResource in mResources:
		mResourceId, muResourceType, nibbles, resource_path, resource_path_body = mResource
		
		resource0_data = resource1_data = resource2_data = b''
		disk0_data = disk1_data = disk2_data = b''
		
		with open(resource_path, "rb") as f:
			resource0_data = f.read()
		if muFlags == 0x7 or muFlags == 0xF:
			disk0_data = zlib.compress(resource0_data, 9)
		else:
			disk0_data = resource0_data
		padding = calculate_padding(len(disk0_data), 0x10)
		
		if resource_path_body != "":
			with open(resource_path_body, "rb") as f:
				resource1_data = f.read()
			if muFlags == 0x7 or muFlags == 0xF:
				disk1_data = zlib.compress(resource1_data, 9)
			else:
				disk1_data = resource1_data
			padding_disk1 = calculate_padding(len(disk1_data), 0x80)
			
			mResource.append([len(resources_data), len(resources_data_body), 0])
			
			resources_data_body += disk1_data
			resources_data_body += bytearray([0])*padding_disk1
		else:
			mResource.append([len(resources_data), 0, 0])
		
		resources_data += disk0_data
		resources_data += bytearray([0])*padding
		
		mResource.append([len(resource0_data), len(resource1_data), len(resource2_data)])
		mResource.append([len(disk0_data), len(disk1_data), len(disk2_data)])
		
		
		# ImportCount and Offset
		muImportCount = 0
		muImportOffset = 0
		muImportHash = 0
		
		if muResourceType in ['Material', 'Renderable', 'MaterialTechnique', 'TextureState', 'AptDataHeaderType', 'Font', 'InstanceList',
							  'IdList', 'Model', 'Shader', 'GraphicsSpec', 'ParticleDescriptionCollection', 'WheelGraphicsSpec',
							  'PropGraphicsList', 'EnvironmentKeyframe', 'EnvironmentTimeLine', 'GraphicsStub', 'FlaptFile']:
			with open(resource_path, "rb") as f:
				if muResourceType == 'Material':
					f.seek(0x8, 0)
					num_shader = 1
					num_material_states = struct.unpack("<B", f.read(0x1))[0]
					num_texture_states = struct.unpack("<B", f.read(0x1))[0]
					muImportCount = num_shader + num_material_states + num_texture_states
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'Renderable':
					f.seek(0x12, 0)
					num_meshes = struct.unpack("<H", f.read(0x2))[0]
					meshes_table_pointer = struct.unpack("<i", f.read(0x4))[0]
					f.seek(meshes_table_pointer, 0)
					meshes_data_pointer = struct.unpack("<%di" % num_meshes, f.read(0x4*num_meshes))
					num_vertex_descriptors_total = 0
					for i in range(0, num_meshes):
						f.seek(meshes_data_pointer[i] + 0x54, 0)
						num_vertex_descriptors_total += struct.unpack("<B", f.read(0x1))[0]
					del meshes_data_pointer
					muImportCount = num_meshes + num_vertex_descriptors_total
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'MaterialTechnique':
					muImportCount = 2
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10	# Only seem on console version, but treating as PC on muImportHash
					
				elif muResourceType == 'TextureState':
					muImportCount = 1
					muImportOffset = 0x40
					
				elif muResourceType == 'AptDataHeaderType':
					f.seek(0x14, 0)
					fileSize = struct.unpack("<I", f.read(0x4))[0]
					fileSize += calculate_padding(fileSize, 0x10)
					muImportCount = int((os.path.getsize(resource_path) - fileSize)/0x10)
					if muImportCount == 0:
						muImportOffset = 0
					else:
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'Font':
					f.seek(0x12C, 0)
					muNumTexturePages = struct.unpack("<I", f.read(0x4))[0]
					muImportCount = muNumTexturePages
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'InstanceList':
					mpaInstances, muArraySize = struct.unpack("<II", f.read(0x8))
					muImportOffset = mpaInstances + 0x50*muArraySize
					muImportCount = muArraySize
					
				elif muResourceType == 'IdList':
					#muImportOffset = struct.unpack("<I", f.read(0x4))[0]
					#muImportCount = struct.unpack("<I", f.read(0x4))[0]
					muImportOffset = 0
					muImportCount = 0
						
				elif muResourceType == 'Model':
					f.seek(0x10, 0)
					mu8NumRenderables = struct.unpack("<B", f.read(0x1))[0]
					muImportCount = mu8NumRenderables
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'Shader':
					f.seek(0x4, 0)
					num_resource_pairs = struct.unpack("<B", f.read(0x1))[0]
					muImportCount = num_resource_pairs*2
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'GraphicsSpec':
					f.seek(0x4, 0)
					muPartsCount = struct.unpack("<I", f.read(0x4))[0]
					f.seek(0xC, 0)
					muShatteredGlassPartsCount = struct.unpack("<I", f.read(0x4))[0]
					muImportCount = muPartsCount + muShatteredGlassPartsCount
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'ParticleDescriptionCollection':
					f.seek(0x4, 0)
					muTableSize = struct.unpack("<I", f.read(0x4))[0]
					muImportCount = muTableSize
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'WheelGraphicsSpec':
					_, mpWheelModel, mpCaliperModel = struct.unpack("<Iii", f.read(0xC))
					muImportCount = 1
					if mpCaliperModel != -1:
						muImportCount = 2
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'PropGraphicsList':
					muSizeInBytes, _ = struct.unpack("<II", f.read(0x8))
					muNumberOfPropModels = struct.unpack("<I", f.read(0x4))[0]
					muNumberOfPropPartModels = struct.unpack("<I", f.read(0x4))[0]
					muImportCount = muNumberOfPropModels + muNumberOfPropPartModels
					if muImportCount == 0:
						muImportOffset = 0
					else:
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'EnvironmentKeyframe':
					muImportCount = 1
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'EnvironmentTimeLine':
					f.seek(0x8, 0)
					mpLocationDatii = struct.unpack("<I", f.read(0x4))[0]
					f.seek(mpLocationDatii, 0)
					muKeyframeCnt = struct.unpack("<I", f.read(0x4))[0]
					muImportCount = muKeyframeCnt
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'GraphicsStub':
					muImportCount = 2
					muImportOffset = 0x10
					
				elif muResourceType == 'FlaptFile':
					f.seek(0x4, 0)
					muSizeInBytes = struct.unpack("<I", f.read(0x4))[0]
					muImportOffset = muSizeInBytes
					muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
				
				for i in range(0, muImportCount):
					f.seek(muImportOffset + i*0x10, 0)
					muImportHash = muImportHash | struct.unpack("<I", f.read(0x4))[0]
		
		mResource.extend([int(muImportOffset), muImportCount, muImportHash])
	
	padding = calculate_padding(len_resource_entries_data + len(resources_data), 0x80)
	padding2 = calculate_padding(len_resource_entries_data + len(resources_data) + padding + len(resources_data_body), 0x80)
	mauResourceDataOffset = [*mauResourceDataOffset]
	mauResourceDataOffset[0] = muResourceEntriesOffset + muResourceEntriesCount*0x40
	mauResourceDataOffset[1] = mauResourceDataOffset[0] + len(resources_data) + padding
	mauResourceDataOffset[2] = mauResourceDataOffset[1] + len(resources_data_body) + padding2
	
	with open(output_path, "wb") as f:
		f.write(macMagicNumber.encode('utf-8'))
		f.write(struct.pack('<I', muVersion))
		f.write(struct.pack('<I', muPlatform))
		f.write(struct.pack('<I', muDebugDataOffset))
		f.write(struct.pack('<I', muResourceEntriesCount))
		f.write(struct.pack('<I', muResourceEntriesOffset))
		f.write(struct.pack('<III', *mauResourceDataOffset))
		f.write(struct.pack('<I', muFlags))
		f.seek(0x8, 1)
		
		f.write(debug_data)
		
		for mResource in mResources:
			mResourceId = mResource[0]
			muResourceType = mResource[1]
			nibbles = mResource[2]
			mauDiskOffset = mResource[5]
			mauUncompressedSize = mResource[6]
			mauSizeOnDisk = mResource[7]
			muImportOffset = mResource[8]
			muImportCount = mResource[9]
			muImportHash = mResource[10]
			
			muResourceTypeId, nibbles = get_resourcetypeid_nibble(muResourceType)
			
			mauUncompressedSizeAndAlignment = [mauUncompressedSize[i] + nibbles[i] for i in range(3)]
			
			f.write(id_to_bytes(mResourceId))
			f.write(struct.pack("<I", 0))
			f.write(struct.pack("<I", muImportHash))
			f.write(struct.pack("<I", 0))
			f.write(struct.pack("<III", *mauUncompressedSizeAndAlignment))
			f.write(struct.pack("<III", *mauSizeOnDisk))
			f.write(struct.pack("<III", *mauDiskOffset))
			f.write(struct.pack("<I", muImportOffset))
			f.write(struct.pack("<I", muResourceTypeId))
			f.write(struct.pack("<H", muImportCount))
			f.write(struct.pack("<B", 0))
			f.write(struct.pack("<B", 0))
		
		f.write(resources_data)
		f.write(bytearray([0])*padding)
		f.write(resources_data_body)
		f.write(bytearray([0])*padding2)
	
	return 0


def pack_bundle_mw(resource_entries_path, output_directory, output_name):
	directory_path = os.path.dirname(resource_entries_path)
	output_path = os.path.join(output_directory, output_name)
	len_resource_entries_data = os.path.getsize(resource_entries_path)
	
	with open(resource_entries_path, "rb") as f:
		try:
			macMagicNumber = str(f.read(0x4), 'ascii')
		except:
			print("Error: not a valid bundle. Magic number (bnd2) is incorrect.")
			return 1
		if macMagicNumber != 'bnd2':
			print("Error: not a valid bundle. Magic number (bnd2) is incorrect.")
			return 1
		
		data_type = ["H", 0x2]
		numDataOffsets = 4
		
		muVersion = struct.unpack("<%s" % data_type[0], f.read(data_type[1]))[0]
		muPlatform = struct.unpack("<%s" % data_type[0], f.read(data_type[1]))[0]
		
		if muPlatform != 0x1:
			print("Error: bundle platform not supported yet. Select a PC file version.")
			return 1
		
		muDebugDataOffset = struct.unpack("<I", f.read(0x4))[0]
		muResourceEntriesCount = struct.unpack("<I", f.read(0x4))[0]
		muResourceEntriesOffset = struct.unpack("<I", f.read(0x4))[0]
		mauResourceDataOffset = struct.unpack("<%dI" % numDataOffsets, f.read(numDataOffsets*0x4))
		muFlags = struct.unpack("<I", f.read(0x4))[0]
		pad1 = struct.unpack("<I", f.read(0x4))[0]
		pad2 = struct.unpack("<I", f.read(0x4))[0]
		
		muResourceEntriesCount_verification = (len_resource_entries_data - muResourceEntriesOffset)//0x48
		if muResourceEntriesCount != muResourceEntriesCount_verification:
			print("Warning: muResourceEntriesCount does not match the number of resource entries. It will be used %d" % muResourceEntriesCount_verification)
			muResourceEntriesCount = muResourceEntriesCount_verification
		
		debug_data = f.read(muResourceEntriesOffset - f.tell())
		
		mResources = []
		for i in range(0, muResourceEntriesCount):
			f.seek(muResourceEntriesOffset + i*0x48, 0)
			mResourceId = bytes_to_id(f.read(0x4))
			countBlock, null = struct.unpack("<2B", f.read(0x2))	# null always equal to zero
			count, isIdInteger = struct.unpack("<2B", f.read(0x2))	# isIdInteger seems to be related with CRC32 ids or unique IDs; always zero or one
			f.seek(0x34, 1)
			muResourceTypeId = struct.unpack("<I", f.read(0x4))[0]
			f.seek(0x2, 1)
			unused_muFlags = struct.unpack("<B", f.read(0x1))[0]
			muStreamIndex = struct.unpack("<B", f.read(0x1))[0]
			
			muResourceType, nibbles = get_resourcetype_nibble_mw(muResourceTypeId)
			
			mResourceId_ = mResourceId
			if countBlock != 0:
				mResourceId += "_" + str(countBlock) 
				if count != 0:
					mResourceId += "_" + str(count)
			elif countBlock == 0 and count != 0:
				mResourceId += "_" + str(countBlock)
				mResourceId += "_" + str(count)
			
			resource_dir = os.path.join(directory_path, muResourceType)
			resource_path = os.path.join(resource_dir, mResourceId + ".dat")
			if not os.path.isfile(resource_path):
				resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + ".dat")
				if not os.path.isfile(resource_path_alternative):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + ".dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + ".dat")
						if not os.path.isfile(resource_path_alternative):
							print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + ".dat", resource_path))
							return 1
				resource_path = resource_path_alternative
			
			resource_path_body = ""
			if muResourceType == "Raster" or muResourceType == "Texture":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_texture.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_texture.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_texture.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_texture.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_texture.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			elif muResourceType == "Renderable":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_model.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_model.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_model.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_model.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_model.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			
			elif muResourceType == "ShaderProgramBuffer":
				resource_path_body = os.path.join(resource_dir, mResourceId + "_unknown.dat")
				if not os.path.isfile(resource_path_body):
					resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "-") + "_unknown.dat")
					if not os.path.isfile(resource_path_alternative):
						resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", " ") + "_unknown.dat")
						if not os.path.isfile(resource_path_alternative):
							resource_path_alternative = os.path.join(resource_dir, mResourceId.replace("_", "") + "_unknown.dat")
							if not os.path.isfile(resource_path_alternative):
								print("Error: failed to get %s %s: no such file in '%s'." % (muResourceType.lower(), mResourceId + "_unknown.dat", resource_path_body))
								return 1
					resource_path_body = resource_path_alternative
			
			mResourceId = mResourceId_
			mResources.append([mResourceId, muResourceType, nibbles, resource_path, resource_path_body, countBlock, count, isIdInteger, muStreamIndex])
	
	resources_data = b''
	resources_data_body = b''
	resources_data2 = b''
	
	mauUncompressedSizes = []
	mauSizesOnDisk = []
	mauDiskOffsets = []
	
	for mResource in mResources:
		mResourceId, muResourceType, nibbles, resource_path, resource_path_body, countBlock, count, isIdInteger, muStreamIndex = mResource
		
		resource0_data = resource1_data = resource2_data = resource3_data = b''
		disk0_data = disk1_data = disk2_data = disk3_data = b''
		
		with open(resource_path, "rb") as f:
			resource0_data = f.read()
		if muFlags == 0x1 or muFlags == 0x5 or muFlags == 0x9 or muFlags == 0x21 or muFlags == 0x29:
			disk0_data = zlib.compress(resource0_data, 9)
		else:
			disk0_data = resource0_data
		#padding = calculate_padding(len(disk0_data), 0x10)
		padding = 0
		
		if resource_path_body != "":
			with open(resource_path_body, "rb") as f:
				resource1_data = f.read()
			if muFlags == 0x1 or muFlags == 0x5 or muFlags == 0x9 or muFlags == 0x21 or muFlags == 0x29:
				disk1_data = zlib.compress(resource1_data, 9)
			else:
				disk1_data = resource1_data
			#padding_disk1 = calculate_padding(len(disk1_data), 0x80)
			padding_disk1 = 0
			
			mResource.append([len(resources_data), len(resources_data_body), 0, 0])
			
			resources_data_body += disk1_data
			resources_data_body += bytearray([0])*padding_disk1
		else:
			mResource.append([len(resources_data), 0, 0, 0])
		
		resources_data += disk0_data
		resources_data += bytearray([0])*padding
		
		mResource.append([len(resource0_data), len(resource1_data), len(resource2_data), len(resource3_data)])
		mResource.append([len(disk0_data), len(disk1_data), len(disk2_data), len(disk3_data)])
		
		
		# ImportCount and Offset
		muImportCount = 0
		muImportOffset = 0
		muImportHash = 0
		
		if muResourceType in ['InstanceList', 'CharacterSpec', 'GraphicsSpec', 'Model', 'Renderable', 'Material', 'GenesysObject', 'GenesysType', 'VehicleSound',
							  'PropInstanceList', 'PropObject', 'WorldObject', 'GroundcoverCollection', 'ReverbRoadData', 'TrafficData', 'CameraTakeList',
							  'DynamicInstanceList', 'ZoneHeader', 'CompoundObject', 'CompoundInstanceList', 'LightInstanceList', 'Font',
							  'BearEffect', 'Shader', 'VertexProgramState']:
			
			with open(resource_path, "rb") as f:
				if muResourceType == 'InstanceList': #ok
					if os.path.getsize(resource_path) <= 0x20:
						muImportCount = 0
						muImportOffset = 0
					else:
						f.seek(os.path.getsize(resource_path) - 0x8, 0)
						check = f.read(0x4)
						count = 1
						while check != b'\x10\x00\x00\x00':
							f.seek(-0x14, 1)
							check = f.read(0x4)
							count = count + 1
						muImportCount = count
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == 'CharacterSpec': #ok
					f.seek(0x10, 0)
					muImportCount = struct.unpack("<B", f.read(0x1))[0]
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == 'GraphicsSpec': #ok
					f.seek(-0x8, 2)
					last_resource_pointer = struct.unpack("<I", f.read(0x4))[0]
					mpResourceIds = last_resource_pointer + 0x4
					mpResourceIds += calculate_padding(mpResourceIds, 0x10)
					
					f.seek(0x0, 0)
					mppModels = struct.unpack("<I", f.read(0x4))[0]
					f.seek(0x10, 0)
					muPartsCount = struct.unpack("<B", f.read(0x1))[0]
					if mppModels >= last_resource_pointer:
						mpResourceIds = mppModels + 4*muPartsCount
						mpResourceIds += calculate_padding(mpResourceIds, 0x10)
					
					muImportCount = int((os.path.getsize(resource_path) - mpResourceIds)/0x10)
					muImportOffset = mpResourceIds
				
				elif muResourceType == 'Model': #ok
					f.seek(0x0, 0)
					pointer = struct.unpack("<i", f.read(0x4))[0]
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = struct.unpack("<i", f.read(0x4))[0]
					count = 1
					while check != pointer:
						f.seek(-0x14, 1)
						check = struct.unpack("<i", f.read(0x4))[0]
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					
				elif muResourceType == 'Renderable': #ok
					f.seek(0x12, 0)
					num_meshes = struct.unpack("<H", f.read(0x2))[0]
					meshes_table_pointer = struct.unpack("<i", f.read(0x4))[0]
					f.seek(meshes_table_pointer, 0)
					intPosition1 = struct.unpack("<i", f.read(0x4))[0]
					MaterialPointer = intPosition1 + 0x20
					f.seek(intPosition1 + num_meshes*0x60, 0)
					for j in range(0, os.path.getsize(resource_path) - (intPosition1 + num_meshes*0x60)):
						f.seek(0x8, 1)
						MatPointer = struct.unpack("<i", f.read(0x4))[0]
						if MatPointer == MaterialPointer:
							muImportOffset = f.tell() - 0xC
							muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
							break
						f.seek(0x4, 1)
				
				elif muResourceType == 'Material': #ok
					f.seek(0x6, 0)
					muImportOffset = struct.unpack("<H", f.read(0x2))[0]
					muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
				
				elif muResourceType == 'GenesysObject': #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x00\x00\x00\x80':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "GenesysType": #ok
					f.seek(0x0, 0)
					unkbyte0 = struct.unpack("<B", f.read(0x1))[0]
					unkbyte1 = struct.unpack("<B", f.read(0x1))[0]
					unkbyte2 = struct.unpack("<B", f.read(0x1))[0]
					if unkbyte1 == 0x6:
						pointer = b'\x24\x00\x00\x00'
					else:
						pointer = b'\x04\x00\x00\x00'
					if unkbyte2 > 0:
						f.seek(0x20, 0)
						unkint = struct.unpack("<i", f.read(0x4))[0]
						f.seek(0x8, 0)
						unkint2 = struct.unpack("<i", f.read(0x4))[0]
						if unkint > 0 or unkint2 != 0:
							f.seek(os.path.getsize(resource_path) - 0x8, 0)
							check = f.read(0x4)
							count = 1
							while check != pointer:
								f.seek(-0x14, 1)
								check = f.read(0x4)
								count = count + 1
								if f.tell() < unkint:						# EDITED 09 Oct 2019
									break
							if f.tell() > unkint:
								muImportCount = count
								muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == 'VehicleSound': #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x10\x00\x00\x80':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "PropInstanceList": #ok
					f.seek(0x8, 0)
					muImportCount = struct.unpack("<i", f.read(0x4))[0]
					if muImportCount == 0:
						muImportOffset = 0
					else:
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "PropObject": #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x04\x00\x00\x00':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "WorldObject": #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x04\x00\x00\x00':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "GroundcoverCollection":
					f.seek(0x3C, 0)
					int_offset = struct.unpack("<i", f.read(0x4))[0]
					int_offset += calculate_padding(int_offset, 0x10)
					if int_offset < os.path.getsize(resource_path) and int_offset > 0:
						f.seek(int_offset + 0x8, 0)
						check = f.read(0x4)
						while check != b'\x40\x00\x00\x80':
							f.seek(0xC, 1)
							check = f.read(0x4)
						muImportOffset = f.tell() - 0xC
						muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
				
				elif muResourceType == "ReverbRoadData": #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x48\x00\x00\x80':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "TrafficData": #ok
					f.seek(0x14, 0)
					muImportCount_a = struct.unpack("<i", f.read(0x4))[0]
					f.seek(0x1C, 0)
					muImportCount_b = struct.unpack("<i", f.read(0x4))[0]
					muImportCount = muImportCount_a + muImportCount_b
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "CameraTakeList": #ok
					f.seek(0xC, 0)
					muImportCount = struct.unpack("<i", f.read(0x4))[0]
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "DynamicInstanceList": #ok
					f.seek(0x8, 0)
					muImportCount = struct.unpack("<i", f.read(0x4))[0]
					if muImportCount == 0:
						muImportOffset = 0
					else:
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "ZoneHeader": #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x04\x00\x00\x80':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "CompoundObject": #ok
					f.seek(os.path.getsize(resource_path) - 0x8, 0)
					check = f.read(0x4)
					count = 1
					while check != b'\x04\x00\x00\x00':
						f.seek(-0x14, 1)
						check = f.read(0x4)
						count = count + 1
					muImportCount = count
					muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "CompoundInstanceList": #ok
					if os.path.getsize(resource_path) <= 0x10:
						muImportCount = 0
						muImportOffset = 0
					else:
						f.seek(os.path.getsize(resource_path) - 0x8, 0)
						check = f.read(0x4)
						count = 1
						while check != b'\x50\x00\x00\x80':
							f.seek(-0x14, 1)
							check = f.read(0x4)
							count = count + 1
						muImportCount = count
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
				
				elif muResourceType == "LightInstanceList": #ok
					f.seek(0x8, 0)
					muImportCount = struct.unpack("<i", f.read(0x4))[0]
					if muImportCount > 0:
						muImportOffset = os.path.getsize(resource_path) - muImportCount*0x10
					else:
						muImportOffset = 0
				
				elif muResourceType == "Font": #ok
					f.seek(0x4, 0)
					muImportOffset = struct.unpack("<I", f.read(0x4))[0]
					muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
					if muImportCount == 0:
						muImportOffset = 0
				
				elif muResourceType == "BearEffect": #ok
					f.seek(0x14, 0)
					muImportOffset = struct.unpack("<I", f.read(0x4))[0]
					muImportOffset += calculate_padding(muImportOffset, 0x10)
					muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
					if muImportCount == 0:
						muImportOffset = 0
				
				elif muResourceType == "Shader": #ok
					f.seek(0x12, 0)
					muImportOffset = struct.unpack("<H", f.read(0x2))[0]
					muImportCount = int((os.path.getsize(resource_path) - muImportOffset)/0x10)
				
				elif muResourceType == "VertexProgramState": #ok
					muImportCount = 2
					muImportOffset = 0x10
				
				for i in range(0, muImportCount):
					f.seek(muImportOffset + i*0x10, 0)
					muImportHash = muImportHash | struct.unpack("<I", f.read(0x4))[0]
		
		mResource.extend([int(muImportOffset), muImportCount, muImportHash])
	
	#padding = calculate_padding(len_resource_entries_data + len(resources_data), 0x80)
	padding = 0
	#padding2 = calculate_padding(len_resource_entries_data + len(resources_data) + padding + len(resources_data_body), 0x80)
	padding2 = 0
	mauResourceDataOffset = [*mauResourceDataOffset]
	mauResourceDataOffset[0] = muResourceEntriesOffset + muResourceEntriesCount*0x48
	mauResourceDataOffset[1] = mauResourceDataOffset[0] + len(resources_data) + padding
	mauResourceDataOffset[2] = mauResourceDataOffset[1] + len(resources_data_body) + padding2
	mauResourceDataOffset[3] = mauResourceDataOffset[2]
	
	if muDebugDataOffset > mauResourceDataOffset[3]:
		muDebugDataOffset = mauResourceDataOffset[3]
	
	with open(output_path, "wb") as f:
		f.write(macMagicNumber.encode('utf-8'))
		f.write(struct.pack('<%s' % data_type[0], muVersion))
		f.write(struct.pack('<%s' % data_type[0], muPlatform))
		f.write(struct.pack('<I', muDebugDataOffset))
		f.write(struct.pack('<I', muResourceEntriesCount))
		f.write(struct.pack('<I', muResourceEntriesOffset))
		f.write(struct.pack('<%dI' % numDataOffsets, *mauResourceDataOffset))
		f.write(struct.pack('<I', muFlags))
		f.write(struct.pack('<I', pad1))
		f.write(struct.pack('<I', pad2))
		
		f.write(debug_data)
		
		for mResource in mResources:
			mResourceId = mResource[0]
			muResourceType = mResource[1]
			nibbles = mResource[2]
			countBlock = mResource[5]
			count = mResource[6]
			isIdInteger = mResource[7]
			muStreamIndex = mResource[8]
			mauDiskOffset = mResource[9]
			mauUncompressedSize = mResource[10]
			mauSizeOnDisk = mResource[11]
			muImportOffset = mResource[12]
			muImportCount = mResource[13]
			muImportHash = mResource[14]
			
			muResourceTypeId, nibbles = get_resourcetypeid_nibble_mw(muResourceType)
			
			mauUncompressedSizeAndAlignment = [mauUncompressedSize[i] + nibbles[i] for i in range(numDataOffsets)]
			
			f.write(id_to_bytes(mResourceId))
			f.write(struct.pack("<B", countBlock))
			f.write(struct.pack("<B", 0))
			f.write(struct.pack("<B", count))
			f.write(struct.pack("<B", isIdInteger))
			#f.write(struct.pack("<I", muImportHash))
			#f.write(struct.pack("<I", 0))
			f.write(struct.pack("<%dI" % numDataOffsets, *mauUncompressedSizeAndAlignment))
			f.write(struct.pack("<%dI" % numDataOffsets, *mauSizeOnDisk))
			f.write(struct.pack("<%dI" % numDataOffsets, *mauDiskOffset))
			f.write(struct.pack("<I", muImportOffset))
			f.write(struct.pack("<I", muResourceTypeId))
			f.write(struct.pack("<H", muImportCount))
			f.write(struct.pack("<B", 0))
			f.write(struct.pack("<B", muStreamIndex))
			f.write(struct.pack("<I", 0))
		
		f.write(resources_data)
		f.write(bytearray([0])*padding)
		f.write(resources_data_body)
		f.write(bytearray([0])*padding2)
	
	return 0


def unpack_bundle_bndl(f, save_directory, ids_table_name="IDsList.BIN", endian=">"):
	f.seek(0x0, 0)
	mauResourceDataOffset = []
	mauResourceDataAlignment = []
	macMagicNumber = str(f.read(0x4), 'ascii')
	muVersion = struct.unpack("%sI" % endian, f.read(0x4))[0]
	muResourceEntriesCount = struct.unpack("%sI" % endian, f.read(0x4))[0]
	for i in range(0, 5):
		mauResourceDataOffset.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
		mauResourceDataAlignment.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
	
	resources_memory_address = struct.unpack("%s5I" % endian, f.read(0x14))					#?
	resource_ids_offset = struct.unpack("%sI" % endian, f.read(0x4))[0]						#?
	muResourceEntriesOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
	imports_offset = struct.unpack("%sI" % endian, f.read(0x4))[0]							#?
	mauResourceDataOffset.insert(0, struct.unpack("%sI" % endian, f.read(0x4))[0])
	muPlatform = struct.unpack("%sI" % endian, f.read(0x4))[0]
	muFlags = struct.unpack("%sI" % endian, f.read(0x4))[0]
	num_compressed_resources = struct.unpack("%sI" % endian, f.read(0x4))[0]
	compression_information_offset = struct.unpack("%sI" % endian, f.read(0x4))[0]
	unk0x68 = struct.unpack("%sI" % endian, f.read(0x4))[0]
	unk0x6C = struct.unpack("%sI" % endian, f.read(0x4))[0]
	
	mauResourceDataOffset_0 = mauResourceDataOffset[0]
	mauResourceDataOffset[0] = 0
	mauResourceDataOffset[2] = mauResourceDataOffset[1]
	mauResourceDataOffset[1] = 0
	mauResourceDataOffset[3] = 0
	
	# mResourceId
	f.seek(resource_ids_offset, 0)
	maResourceId = []
	for i in range(0, muResourceEntriesCount):
		f.seek(resource_ids_offset + i*0x8, 0)
		_ = struct.unpack("%sI" % endian, f.read(0x4))[0]
		mResourceId = bytes_to_id(f.read(0x4))
		maResourceId.append(mResourceId)
	
	# UncompressedSize
	f.seek(compression_information_offset, 0)
	mauUncompressedSizes = []
	mauUncompressedAlignments = []
	for i in range(0, num_compressed_resources):
		f.seek(compression_information_offset + i*0x28, 0)
		mauUncompressedSize = []
		mauUncompressedAlignment = []
		for j in range(0, 5):
			mauUncompressedSize.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
			mauUncompressedAlignment.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
		mauUncompressedSizes.append(mauUncompressedSize)
		mauUncompressedAlignments.append(mauUncompressedAlignment)
	
	f.seek(muResourceEntriesOffset, 0)
	for i in range(0, muResourceEntriesCount):
		mauSizeOnDisk = []
		mauAlignmentOnDisk = []
		mauDiskOffset = []
		mauAlignmentOnDiskOffset = []
		f.seek(muResourceEntriesOffset + i*0x70, 0)
		resource_data_memory_address = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muImportOffset = struct.unpack("%sI" % endian, f.read(0x4))[0]
		muResourceTypeId = struct.unpack("%sI" % endian, f.read(0x4))[0]
		for j in range(0, 5):
			mauSizeOnDisk.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
			mauAlignmentOnDisk.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
		for j in range(0, 5):
			mauDiskOffset.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
			mauAlignmentOnDiskOffset.append(struct.unpack("%sI" % endian, f.read(0x4))[0])
		resource_memory_address = struct.unpack("%s5I" % endian, f.read(0x14))
		
		# Imports
		if muImportOffset != 0:
			f.seek(muImportOffset, 0)
			muImportCount = struct.unpack("%sI" % endian, f.read(0x4))[0]
			f.seek(0x4, 1)
			ImportEntry = f.read(muImportCount*0x10)
		muResourceType, nibbles = get_resourcetype_nibble(muResourceTypeId)
		
		# Unpacking data
		resource_dir = os.path.join(save_directory, muResourceType)
		os.makedirs(resource_dir, exist_ok = True)
		
		for j in range(0, 5):
			#if mauUncompressedSizes[i][j] == 0:
			if mauSizeOnDisk[j] == 0:
				continue
			f.seek(mauResourceDataOffset[j] + mauDiskOffset[j], 0)
			resource_data = f.read(mauSizeOnDisk[j])
			
			if muFlags == 0x1:
				zobj = zlib.decompressobj()
				if endian == "<":
					try:
						resource_data = zobj.decompress(resource_data, mauUncompressedSizes[i][j])
					except:
						resource_data = zobj.decompress(resource_data)
				else:
					resource_data = zobj.decompress(resource_data)
			
			resource_path = os.path.join(resource_dir, maResourceId[i] + ".dat")
			
			if j == 1:
				if muResourceType == "ShaderProgramBuffer":
					resource_path = os.path.join(resource_dir, maResourceId[i] + "_unknown.dat")
				else:
					resource_path = os.path.join(resource_dir, maResourceId[i] + "_unknown.dat")
			elif j == 2:
				if muResourceType == "Raster":
					resource_path = os.path.join(resource_dir, maResourceId[i] + "_texture.dat")
				elif muResourceType == "Renderable":
					resource_path = os.path.join(resource_dir, maResourceId[i] + "_model.dat")
				elif muResourceType == "VFXMeshCollection":
					resource_path = os.path.join(resource_dir, maResourceId[i] + "_model.dat")
				else:
					resource_path = os.path.join(resource_dir, maResourceId[i] + "_unknown" + str(j) + ".dat")
			elif j > 0:
				resource_path = os.path.join(resource_dir, maResourceId[i] + "_unknown" + str(j) + ".dat")
			
			with open(resource_path, "wb") as g:
				g.write(resource_data)
		
		if muImportOffset != 0:
			resource_imports_path = os.path.join(resource_dir, maResourceId[i] + "_imports.dat")
			with open(resource_imports_path, "wb") as g:
				g.write(ImportEntry)
	
	ids_path = os.path.join(save_directory, ids_table_name)
	with open(ids_path, "wb") as g:
		f.seek(0x0, 0)
		g.write(f.read(muResourceEntriesOffset))
	
	#ids_path = os.path.join(save_directory, ids_table_name)
	#with open(ids_path, "wb") as g:
	#	f.seek(muResourceEntriesOffset, 0)
	#	if compression_information_offset != 0:
	#		g.write(f.read(compression_information_offset - muResourceEntriesOffset))
	#	elif imports_offset != 0:
	#		g.write(f.read(imports_offset - muResourceEntriesOffset))
	#	elif imports_offset == 0:
	#		g.write(f.read(mauResourceDataOffset_0 - muResourceEntriesOffset))
	
	return 0

def get_resourcetype_nibble(resource_id):
	resource_nibble = {0x00000000: ['Raster', [0x20000000, 0x40000000, 0x0]],
					   0x00000001: ['Material', [0x40000000, 0x0, 0x0]],
					   0x00000002: ['RenderableMesh', [0x40000000, 0x0, 0x0]],
					   0x00000003: ['TextFile', [0x40000000, 0x0, 0x0]],
					   0x00000004: ['DrawIndexParams', [0x40000000, 0x0, 0x0]],
					   0x00000005: ['IndexBuffer', [0x40000000, 0x0, 0x0]],
					   0x00000006: ['MeshState', [0x40000000, 0x0, 0x0]],
					   0x00000009: ['VertexBuffer', [0x40000000, 0x0, 0x0]],
					   0x0000000A: ['VertexDesc', [0x20000000, 0x0, 0x0]],
					   0x0000000B: ['RwMaterialCRC32', [0x40000000, 0x0, 0x0]],
					   0x0000000C: ['Renderable', [0x40000000, 0x40000000, 0x0]],
					   0x0000000D: ['MaterialTechnique', [0x40000000, 0x0, 0x0]],
					   0x0000000E: ['TextureState', [0x40000000, 0x0, 0x0]],
					   0x0000000F: ['MaterialState', [0x40000000, 0x0, 0x0]],
					   0x00000010: ['DepthStencilState', [0x40000000, 0x0, 0x0]],
					   0x00000011: ['RasterizerState', [0x40000000, 0x0, 0x0]],
					   0x00000012: ['ShaderProgramBuffer', [0x40000000, 0x20000000, 0x0]],
					   0x00000014: ['ShaderParameter', [0x40000000, 0x0, 0x0]],
					   0x00000015: ['RenderableAssembly', [0x40000000, 0x0, 0x0]],
					   0x00000016: ['Debug', [0x40000000, 0x0, 0x0]],
					   0x00000017: ['KdTree', [0x40000000, 0x0, 0x0]],
					   0x00000018: ['VoiceHierarchy', [0x40000000, 0x0, 0x0]],
					   0x00000019: ['Snr', [0x40000000, 0x0, 0x0]],
					   0x0000001A: ['InterpreterData', [0x40000000, 0x0, 0x0]],
					   0x0000001B: ['AttribSysSchema', [0x40000000, 0x0, 0x0]],
					   0x0000001C: ['AttribSysVault', [0x40000000, 0x0, 0x0]],
					   0x0000001D: ['EntryList', [0x40000000, 0x0, 0x0]],
					   0x0000001E: ['AptDataHeaderType', [0x40000000, 0x0, 0x0]],
					   0x0000001F: ['GuiPopup', [0x40000000, 0x0, 0x0]],
					   0x00000021: ['Font', [0x40000000, 0x0, 0x0]],
					   0x00000022: ['LuaCode', [0x40000000, 0x0, 0x0]],
					   0x00000023: ['InstanceList', [0x40000000, 0x0, 0x0]],
					   0x00000024: ['CollisionMeshData', [0x40000000, 0x0, 0x0]],
					   0x00000025: ['IdList', [0x40000000, 0x0, 0x0]],
					   0x00000026: ['InstanceCollisionList', [0x40000000, 0x0, 0x0]],
					   0x00000027: ['Language', [0x00000000, 0x0, 0x0]],
					   0x00000028: ['SatNavTile', [0x40000000, 0x0, 0x0]],
					   0x00000029: ['SatNavTileDirectory', [0x40000000, 0x0, 0x0]],
					   0x0000002A: ['Model', [0x20000000, 0x0, 0x0]],
					   0x0000002B: ['ColourCube', [0x40000000, 0x0, 0x0]],
					   0x0000002C: ['HudMessage', [0x40000000, 0x0, 0x0]],
					   0x0000002D: ['HudMessageList', [0x40000000, 0x0, 0x0]],
					   0x0000002E: ['HudMessageSequence', [0x40000000, 0x0, 0x0]],
					   0x0000002F: ['HudMessageSequenceDictionary', [0x40000000, 0x0, 0x0]],
					   0x00000030: ['WorldPainter2D', [0x20000000, 0x0, 0x0]],
					   0x00000031: ['PFXHookBundle', [0x40000000, 0x0, 0x0]],
					   0x00000032: ['Shader', [0x40000000, 0x0, 0x0]],
					   0x00000040: ['RawFile', [0x40000000, 0x0, 0x0]],
					   0x00000041: ['ICETakeDictionary', [0x30000000, 0x0, 0x0]],
					   0x00000042: ['VideoData', [0x20000000, 0x0, 0x0]],
					   0x00000043: ['PolygonSoupList', [0x70000000, 0x0, 0x0]],
					   0x00000045: ['CommsToolListDefinition', [0x50000000, 0x0, 0x0]],
					   0x00000046: ['CommsToolList', [0x50000000, 0x0, 0x0]],
					   0x00000050: ['BinaryFile', [0x40000000, 0x0, 0x0]],
					   0x00000051: ['AnimationCollection', [0x40000000, 0x0, 0x0]],
					   0x00002710: ['CharAnimBankFile', [0x40000000, 0x0, 0x0]],
					   0x00002711: ['WeaponFile', [0x40000000, 0x0, 0x0]],
					   0x0000343E: ['VFXFile', [0x40000000, 0x0, 0x0]],
					   0x0000343F: ['BearFile', [0x40000000, 0x0, 0x0]],
					   0x00003A98: ['BkPropInstanceList', [0x40000000, 0x0, 0x0]],
					   0x0000A000: ['Registry', [0x20000000, 0x0, 0x0]],
					   0x0000A020: ['GenericRwacWaveContent', [0x20000000, 0x0, 0x0]],
					   0x0000A021: ['GinsuWaveContent', [0x20000000, 0x0, 0x0]],
					   0x0000A022: ['AemsBank', [0x20000000, 0x0, 0x0]],
					   0x0000A023: ['Csis', [0x20000000, 0x0, 0x0]],
					   0x0000A024: ['Nicotine', [0x20000000, 0x0, 0x0]],
					   0x0000A025: ['Splicer', [0x20000000, 0x0, 0x0]],
					   0x0000A026: ['FreqContent', [0x40000000, 0x0, 0x0]],
					   0x0000A027: ['VoiceHierarchyCollection', [0x40000000, 0x0, 0x0]],
					   0x0000A028: ['GenericRwacReverbIRContent', [0x40000000, 0x0, 0x0]],
					   0x0000A029: ['SnapshotData', [0x20000000, 0x0, 0x0]],
					   0x0000B000: ['ZoneList', [0x40000000, 0x0, 0x0]],
					   0x00010000: ['LoopModel', [0x00000000, 0x0, 0x0]],
					   0x00010001: ['AISections', [0x40000000, 0x0, 0x0]],
					   0x00010002: ['TrafficData', [0x40000000, 0x0, 0x0]],
					   0x00010003: ['Trigger', [0x40000000, 0x0, 0x0]],
					   0x00010004: ['DeformationModel', [0x40000000, 0x0, 0x0]],
					   0x00010005: ['VehicleList', [0x40000000, 0x0, 0x0]],
					   0x00010006: ['GraphicsSpec', [0x40000000, 0x0, 0x0]],
					   0x00010007: ['PhysicsSpec', [0x40000000, 0x0, 0x0]],
					   0x00010008: ['ParticleDescriptionCollection', [0x40000000, 0x0, 0x0]],
					   0x00010009: ['WheelList', [0x40000000, 0x0, 0x0]],
					   0x0001000A: ['WheelGraphicsSpec', [0x40000000, 0x0, 0x0]],
					   0x0001000B: ['TextureNameMap', [0x40000000, 0x0, 0x0]],
					   0x0001000C: ['ICEList', [0x40000000, 0x0, 0x0]],
					   0x0001000D: ['ICEData', [0x40000000, 0x0, 0x0]],
					   0x0001000E: ['Progression', [0x40000000, 0x0, 0x0]],
					   0x0001000F: ['PropPhysics', [0x40000000, 0x0, 0x0]],
					   0x00010010: ['PropGraphicsList', [0x40000000, 0x0, 0x0]],
					   0x00010011: ['PropInstanceData', [0x40000000, 0x0, 0x0]],
					   0x00010012: ['EnvironmentKeyframe', [0x40000000, 0x0, 0x0]],
					   0x00010013: ['EnvironmentTimeLine', [0x40000000, 0x0, 0x0]],
					   0x00010014: ['EnvironmentDictionary', [0x40000000, 0x0, 0x0]],
					   0x00010015: ['GraphicsStub', [0x20000000, 0x0, 0x0]],
					   0x00010016: ['StaticSoundMap', [0x40000000, 0x0, 0x0]],
					   0x00010018: ['StreetData', [0x40000000, 0x0, 0x0]],
					   0x00010019: ['VFXMeshCollection', [0x40000000, 0x40000000, 0x0]],
					   0x0001001A: ['MassiveLookupTable', [0x40000000, 0x0, 0x0]],
					   0x0001001B: ['VFXPropCollection', [0x40000000, 0x0, 0x0]],
					   0x0001001C: ['StreamedDeformationSpec', [0x40000000, 0x0, 0x0]],
					   0x0001001D: ['ParticleDescription', [0x40000000, 0x0, 0x0]],
					   0x0001001E: ['PlayerCarColours', [0x40000000, 0x0, 0x0]],
					   0x0001001F: ['ChallengeList', [0x40000000, 0x0, 0x0]],
					   0x00010020: ['FlaptFile', [0x40000000, 0x0, 0x0]],
					   0x00010021: ['ProfileUpgrade', [0x40000000, 0x0, 0x0]],
					   0x00010023: ['VehicleAnimation', [0x40000000, 0x0, 0x0]],
					   0x00010024: ['BodypartRemapping', [0x40000000, 0x0, 0x0]],
					   0x00010025: ['LUAList', [0x60000000, 0x0, 0x0]],
					   0x00010026: ['LUAScript', [0x60000000, 0x0, 0x0]],
					   0x00011000: ['BkSoundWeapon', [0x40000000, 0x0, 0x0]],
					   0x00011001: ['BkSoundGunsu', [0x40000000, 0x0, 0x0]],
					   0x00011002: ['BkSoundBulletImpact', [0x40000000, 0x0, 0x0]],
					   0x00011003: ['BkSoundBulletImpactList', [0x40000000, 0x0, 0x0]],
					   0x00011004: ['BkSoundBulletImpactStream', [0x40000000, 0x0, 0x0]]}
	
	return resource_nibble[resource_id]


def get_resourcetype_nibble_mw(resource_id):
	resource_nibble = {	0x00000001 : ['Texture', [0x40000000, 0x40000000, 0x0, 0x0]],
						0x00000002 : ['Material', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000003 : ['VertexDescriptor', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000004 : ['VertexProgramState', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000005 : ['Renderable', [0x40000000, 0x40000000, 0x0, 0x0]],
						0x00000006 : ['MaterialState', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000007 : ['SamplerState', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000008 : ['ShaderProgramBuffer', [0x40000000, 0x40000000, 0x0, 0x0]],
						0x00000014 : ['GenesysType', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000015 : ['GenesysObject', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000030 : ['Font', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000050 : ['InstanceList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000051 : ['Model', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000052 : ['ColourCube', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000053 : ['Shader', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000060 : ['PolygonSoupList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000068 : ['NavigationMesh', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000070 : ['TextFile', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000080 : ['Ginsu', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000081 : ['Wave', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000082 : ['WaveContainerTable', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000083 : ['GameplayLinkData', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000084 : ['WaveDictionary', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000086 : ['Reverb', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000090 : ['ZoneList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000091 : ['WorldPaintMap', [0x40000000, 0x0, 0x0, 0x0]],
						0x000000b0 : ['AnimationList', [0x40000000, 0x0, 0x0, 0x0]],
						0x000000b2 : ['Skeleton', [0x40000000, 0x0, 0x0, 0x0]],
						0x000000b3 : ['Animation', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000105 : ['VehicleList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000106 : ['GraphicsSpec', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000200 : ['AIData', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000201 : ['Language', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000202 : ['TriggerData', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000203 : ['RoadData', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000204 : ['DynamicInstanceList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000205 : ['WorldObject', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000206 : ['ZoneHeader', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000207 : ['VehicleSound', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000209 : ['CharacterSpec', [0x40000000, 0x0, 0x0, 0x0]],
						0x0000020c : ['ReverbRoadData', [0x40000000, 0x0, 0x0, 0x0]],
						0x0000020d : ['CameraTake', [0x40000000, 0x0, 0x0, 0x0]],
						0x0000020e : ['CameraTakeList', [0x40000000, 0x0, 0x0, 0x0]],
						0x0000020f : ['GroundcoverCollection', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000213 : ['LightInstanceList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000214 : ['GroundcoverInstances', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000215 : ['CompoundObject', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000216 : ['CompoundInstanceList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000217 : ['PropObject', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000218 : ['PropInstanceList', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000219 : ['ZoneAmbienceListDataType', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000301 : ['BearEffect', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000302 : ['BearGlobalParameters', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000303 : ['ConvexHull', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000501 : ['HSMData', [0x40000000, 0x0, 0x0, 0x0]],
						0x00000701 : ['TrafficData', [0x40000000, 0x0, 0x0, 0x0]]}
	
	return resource_nibble[resource_id]


def get_resourcetypeid_nibble(resource_type):
	resource_nibble = {'Raster': [0x00000000, [0x20000000, 0x40000000, 0x0]],
					   'Material': [0x00000001, [0x40000000, 0x0, 0x0]],
					   'RenderableMesh': [0x00000002, [0x40000000, 0x0, 0x0]],
					   'TextFile': [0x00000003, [0x40000000, 0x0, 0x0]],
					   'DrawIndexParams': [0x00000004, [0x40000000, 0x0, 0x0]],
					   'IndexBuffer': [0x00000005, [0x40000000, 0x0, 0x0]],
					   'MeshState': [0x00000006, [0x40000000, 0x0, 0x0]],
					   'VertexBuffer': [0x00000009, [0x40000000, 0x0, 0x0]],
					   'VertexDesc': [0x0000000A, [0x20000000, 0x0, 0x0]],
					   'RwMaterialCRC32': [0x0000000B, [0x40000000, 0x0, 0x0]],
					   'Renderable': [0x0000000C, [0x40000000, 0x40000000, 0x0]],
					   'MaterialTechnique': [0x0000000D, [0x40000000, 0x0, 0x0]],
					   'TextureState': [0x0000000E, [0x40000000, 0x0, 0x0]],
					   'MaterialState': [0x0000000F, [0x40000000, 0x0, 0x0]],
					   'DepthStencilState': [0x00000010, [0x40000000, 0x0, 0x0]],
					   'RasterizerState': [0x00000011, [0x40000000, 0x0, 0x0]],
					   'ShaderProgramBuffer': [0x00000012, [0x40000000, 0x20000000, 0x0]],
					   'ShaderParameter': [0x00000014, [0x40000000, 0x0, 0x0]],
					   'RenderableAssembly': [0x00000015, [0x40000000, 0x0, 0x0]],
					   'Debug': [0x00000016, [0x40000000, 0x0, 0x0]],
					   'KdTree': [0x00000017, [0x40000000, 0x0, 0x0]],
					   'VoiceHierarchy': [0x00000018, [0x40000000, 0x0, 0x0]],
					   'Snr': [0x00000019, [0x40000000, 0x0, 0x0]],
					   'InterpreterData': [0x0000001A, [0x40000000, 0x0, 0x0]],
					   'AttribSysSchema': [0x0000001B, [0x40000000, 0x0, 0x0]],
					   'AttribSysVault': [0x0000001C, [0x40000000, 0x0, 0x0]],
					   'EntryList': [0x0000001D, [0x40000000, 0x0, 0x0]],
					   'AptDataHeaderType': [0x0000001E, [0x40000000, 0x0, 0x0]],
					   'GuiPopup': [0x0000001F, [0x40000000, 0x0, 0x0]],
					   'Font': [0x00000021, [0x40000000, 0x0, 0x0]],
					   'LuaCode': [0x00000022, [0x40000000, 0x0, 0x0]],
					   'InstanceList': [0x00000023, [0x40000000, 0x0, 0x0]],
					   'CollisionMeshData': [0x00000024, [0x40000000, 0x0, 0x0]],
					   'IdList': [0x00000025, [0x40000000, 0x0, 0x0]],
					   'InstanceCollisionList': [0x00000026, [0x40000000, 0x0, 0x0]],
					   'Language': [0x00000027, [0x00000000, 0x0, 0x0]],
					   'SatNavTile': [0x00000028, [0x40000000, 0x0, 0x0]],
					   'SatNavTileDirectory': [0x00000029, [0x40000000, 0x0, 0x0]],
					   'Model': [0x0000002A, [0x20000000, 0x0, 0x0]],
					   'ColourCube': [0x0000002B, [0x40000000, 0x0, 0x0]],
					   'HudMessage': [0x0000002C, [0x40000000, 0x0, 0x0]],
					   'HudMessageList': [0x0000002D, [0x40000000, 0x0, 0x0]],
					   'HudMessageSequence': [0x0000002E, [0x40000000, 0x0, 0x0]],
					   'HudMessageSequenceDictionary': [0x0000002F, [0x40000000, 0x0, 0x0]],
					   'WorldPainter2D': [0x00000030, [0x20000000, 0x0, 0x0]],
					   'PFXHookBundle': [0x00000031, [0x40000000, 0x0, 0x0]],
					   'Shader': [0x00000032, [0x40000000, 0x0, 0x0]],
					   'RawFile': [0x00000040, [0x40000000, 0x0, 0x0]],
					   'ICETakeDictionary': [0x00000041, [0x30000000, 0x0, 0x0]],
					   'VideoData': [0x00000042, [0x20000000, 0x0, 0x0]],
					   'PolygonSoupList': [0x00000043, [0x70000000, 0x0, 0x0]],
					   'CommsToolListDefinition': [0x00000045, [0x50000000, 0x0, 0x0]],
					   'CommsToolList': [0x00000046, [0x50000000, 0x0, 0x0]],
					   'BinaryFile': [0x00000050, [0x40000000, 0x0, 0x0]],
					   'AnimationCollection': [0x00000051, [0x40000000, 0x0, 0x0]],
					   'CharAnimBankFile': [0x00002710, [0x40000000, 0x0, 0x0]],
					   'WeaponFile': [0x00002711, [0x40000000, 0x0, 0x0]],
					   'VFXFile': [0x0000343E, [0x40000000, 0x0, 0x0]],
					   'BearFile': [0x0000343F, [0x40000000, 0x0, 0x0]],
					   'BkPropInstanceList': [0x00003A98, [0x40000000, 0x0, 0x0]],
					   'Registry': [0x0000A000, [0x20000000, 0x0, 0x0]],
					   'GenericRwacWaveContent': [0x0000A020, [0x20000000, 0x0, 0x0]],
					   'GinsuWaveContent': [0x0000A021, [0x20000000, 0x0, 0x0]],
					   'AemsBank': [0x0000A022, [0x20000000, 0x0, 0x0]],
					   'Csis': [0x0000A023, [0x20000000, 0x0, 0x0]],
					   'Nicotine': [0x0000A024, [0x20000000, 0x0, 0x0]],
					   'Splicer': [0x0000A025, [0x20000000, 0x0, 0x0]],
					   'FreqContent': [0x0000A026, [0x40000000, 0x0, 0x0]],
					   'VoiceHierarchyCollection': [0x0000A027, [0x40000000, 0x0, 0x0]],
					   'GenericRwacReverbIRContent': [0x0000A028, [0x40000000, 0x0, 0x0]],
					   'SnapshotData': [0x0000A029, [0x20000000, 0x0, 0x0]],
					   'ZoneList': [0x0000B000, [0x40000000, 0x0, 0x0]],
					   'LoopModel': [0x00010000, [0x00000000, 0x0, 0x0]],
					   'AISections': [0x00010001, [0x40000000, 0x0, 0x0]],
					   'TrafficData': [0x00010002, [0x40000000, 0x0, 0x0]],
					   'Trigger': [0x00010003, [0x40000000, 0x0, 0x0]],
					   'DeformationModel': [0x00010004, [0x40000000, 0x0, 0x0]],
					   'VehicleList': [0x00010005, [0x40000000, 0x0, 0x0]],
					   'GraphicsSpec': [0x00010006, [0x40000000, 0x0, 0x0]],
					   'PhysicsSpec': [0x00010007, [0x40000000, 0x0, 0x0]],
					   'ParticleDescriptionCollection': [0x00010008, [0x40000000, 0x0, 0x0]],
					   'WheelList': [0x00010009, [0x40000000, 0x0, 0x0]],
					   'WheelGraphicsSpec': [0x0001000A, [0x40000000, 0x0, 0x0]],
					   'TextureNameMap': [0x0001000B, [0x40000000, 0x0, 0x0]],
					   'ICEList': [0x0001000C, [0x40000000, 0x0, 0x0]],
					   'ICEData': [0x0001000D, [0x40000000, 0x0, 0x0]],
					   'Progression': [0x0001000E, [0x40000000, 0x0, 0x0]],
					   'PropPhysics': [0x0001000F, [0x40000000, 0x0, 0x0]],
					   'PropGraphicsList': [0x00010010, [0x40000000, 0x0, 0x0]],
					   'PropInstanceData': [0x00010011, [0x40000000, 0x0, 0x0]],
					   'EnvironmentKeyframe': [0x00010012, [0x40000000, 0x0, 0x0]],
					   'EnvironmentTimeLine': [0x00010013, [0x40000000, 0x0, 0x0]],
					   'EnvironmentDictionary': [0x00010014, [0x40000000, 0x0, 0x0]],
					   'GraphicsStub': [0x00010015, [0x20000000, 0x0, 0x0]],
					   'StaticSoundMap': [0x00010016, [0x40000000, 0x0, 0x0]],
					   'StreetData': [0x00010018, [0x40000000, 0x0, 0x0]],
					   'VFXMeshCollection': [0x00010019, [0x40000000, 0x40000000, 0x0]],
					   'MassiveLookupTable': [0x0001001A, [0x40000000, 0x0, 0x0]],
					   'VFXPropCollection': [0x0001001B, [0x40000000, 0x0, 0x0]],
					   'StreamedDeformationSpec': [0x0001001C, [0x40000000, 0x0, 0x0]],
					   'ParticleDescription': [0x0001001D, [0x40000000, 0x0, 0x0]],
					   'PlayerCarColours': [0x0001001E, [0x40000000, 0x0, 0x0]],
					   'ChallengeList': [0x0001001F, [0x40000000, 0x0, 0x0]],
					   'FlaptFile': [0x00010020, [0x40000000, 0x0, 0x0]],
					   'ProfileUpgrade': [0x00010021, [0x40000000, 0x0, 0x0]],
					   'VehicleAnimation': [0x00010023, [0x40000000, 0x0, 0x0]],
					   'BodypartRemapping': [0x00010024, [0x40000000, 0x0, 0x0]],
					   'LUAList': [0x00010025, [0x60000000, 0x0, 0x0]],
					   'LUAScript': [0x00010026, [0x60000000, 0x0, 0x0]],
					   'BkSoundWeapon': [0x00011000, [0x40000000, 0x0, 0x0]],
					   'BkSoundGunsu': [0x00011001, [0x40000000, 0x0, 0x0]],
					   'BkSoundBulletImpact': [0x00011002, [0x40000000, 0x0, 0x0]],
					   'BkSoundBulletImpactList': [0x00011003, [0x40000000, 0x0, 0x0]],
					   'BkSoundBulletImpactStream': [0x00011004, [0x40000000, 0x0, 0x0]]}
	
	return resource_nibble[resource_type]


def get_resourcetypeid_nibble_mw(resource_type):
	resource_nibble = {	'Texture': [0x00000001, [0x40000000, 0x40000000, 0x0, 0x0]],
						'Material': [0x00000002, [0x40000000, 0x0, 0x0, 0x0]],
						'VertexDescriptor': [0x00000003, [0x40000000, 0x0, 0x0, 0x0]],
						'VertexProgramState': [0x00000004, [0x40000000, 0x0, 0x0, 0x0]],
						'Renderable': [0x00000005, [0x40000000, 0x40000000, 0x0, 0x0]],
						'MaterialState': [0x00000006, [0x40000000, 0x0, 0x0, 0x0]],
						'SamplerState': [0x00000007, [0x40000000, 0x0, 0x0, 0x0]],
						'ShaderProgramBuffer': [0x00000008, [0x40000000, 0x40000000, 0x0, 0x0]],
						'GenesysType': [0x00000014, [0x40000000, 0x0, 0x0, 0x0]],
						'GenesysObject': [0x00000015, [0x40000000, 0x0, 0x0, 0x0]],
						'Font': [0x00000030, [0x40000000, 0x0, 0x0, 0x0]],
						'InstanceList': [0x00000050, [0x40000000, 0x0, 0x0, 0x0]],
						'Model': [0x00000051, [0x40000000, 0x0, 0x0, 0x0]],
						'ColourCube': [0x00000052, [0x40000000, 0x0, 0x0, 0x0]],
						'Shader': [0x00000053, [0x40000000, 0x0, 0x0, 0x0]],
						'PolygonSoupList': [0x00000060, [0x40000000, 0x0, 0x0, 0x0]],
						'NavigationMesh': [0x00000068, [0x40000000, 0x0, 0x0, 0x0]],
						'TextFile': [0x00000070, [0x40000000, 0x0, 0x0, 0x0]],
						'Ginsu': [0x00000080, [0x40000000, 0x0, 0x0, 0x0]],
						'Wave': [0x00000081, [0x40000000, 0x0, 0x0, 0x0]],
						'WaveContainerTable': [0x00000082, [0x40000000, 0x0, 0x0, 0x0]],
						'GameplayLinkData': [0x00000083, [0x40000000, 0x0, 0x0, 0x0]],
						'WaveDictionary': [0x00000084, [0x40000000, 0x0, 0x0, 0x0]],
						'Reverb': [0x00000086, [0x40000000, 0x0, 0x0, 0x0]],
						'ZoneList': [0x00000090, [0x40000000, 0x0, 0x0, 0x0]],
						'WorldPaintMap': [0x00000091, [0x40000000, 0x0, 0x0, 0x0]],
						'AnimationList': [0x000000b0, [0x40000000, 0x0, 0x0, 0x0]],
						'Skeleton': [0x000000b2, [0x40000000, 0x0, 0x0, 0x0]],
						'Animation': [0x000000b3, [0x40000000, 0x0, 0x0, 0x0]],
						'VehicleList': [0x00000105, [0x40000000, 0x0, 0x0, 0x0]],
						'GraphicsSpec': [0x00000106, [0x40000000, 0x0, 0x0, 0x0]],
						'AIData': [0x00000200, [0x40000000, 0x0, 0x0, 0x0]],
						'Language': [0x00000201, [0x40000000, 0x0, 0x0, 0x0]],
						'TriggerData': [0x00000202, [0x40000000, 0x0, 0x0, 0x0]],
						'RoadData': [0x00000203, [0x40000000, 0x0, 0x0, 0x0]],
						'DynamicInstanceList': [0x00000204, [0x40000000, 0x0, 0x0, 0x0]],
						'WorldObject': [0x00000205, [0x40000000, 0x0, 0x0, 0x0]],
						'ZoneHeader': [0x00000206, [0x40000000, 0x0, 0x0, 0x0]],
						'VehicleSound': [0x00000207, [0x40000000, 0x0, 0x0, 0x0]],
						'CharacterSpec': [0x00000209, [0x40000000, 0x0, 0x0, 0x0]],
						'ReverbRoadData': [0x0000020c, [0x40000000, 0x0, 0x0, 0x0]],
						'CameraTake': [0x0000020d, [0x40000000, 0x0, 0x0, 0x0]],
						'CameraTakeList': [0x0000020e, [0x40000000, 0x0, 0x0, 0x0]],
						'GroundcoverCollection': [0x0000020f, [0x40000000, 0x0, 0x0, 0x0]],
						'LightInstanceList': [0x00000213, [0x40000000, 0x0, 0x0, 0x0]],
						'GroundcoverInstances': [0x00000214, [0x40000000, 0x0, 0x0, 0x0]],
						'CompoundObject': [0x00000215, [0x40000000, 0x0, 0x0, 0x0]],
						'CompoundInstanceList': [0x00000216, [0x40000000, 0x0, 0x0, 0x0]],
						'PropObject': [0x00000217, [0x40000000, 0x0, 0x0, 0x0]],
						'PropInstanceList': [0x00000218, [0x40000000, 0x0, 0x0, 0x0]],
						'ZoneAmbienceListDataType': [0x00000219, [0x40000000, 0x0, 0x0, 0x0]],
						'BearEffect': [0x00000301, [0x40000000, 0x0, 0x0, 0x0]],
						'BearGlobalParameters': [0x00000302, [0x40000000, 0x0, 0x0, 0x0]],
						'ConvexHull': [0x00000303, [0x40000000, 0x0, 0x0, 0x0]],
						'HSMData': [0x00000501, [0x40000000, 0x0, 0x0, 0x0]],
						'TrafficData': [0x00000701, [0x40000000, 0x0, 0x0, 0x0]]}
	
	return resource_nibble[resource_type]


def bytes_to_id(id):
	id = binascii.hexlify(id)
	id = str(id,'ascii')
	id = id.upper()
	id = '_'.join([id[x : x+2] for x in range(0, len(id), 2)])
	return id


def id_to_bytes(id):
	id_old = id
	id = id.replace('_', '')
	id = id.replace(' ', '')
	id = id.replace('-', '')
	if len(id) != 8:
		print("ERROR: ResourceId not in the proper format: %s" % id_old)
	try:
		int(id, 16)
	except ValueError:
		print("ERROR: ResourceId is not a valid hexadecimal string: %s" % id_old)
	return bytearray.fromhex(id)


def calculate_padding(lenght, alignment):
	division1 = (lenght/alignment)
	division2 = math.ceil(lenght/alignment)
	padding = int((division2 - division1)*alignment)
	return padding


def manual_command_handler(command):
	if command == "-h" or command == "--help":
		print()
		print("Criterion's games bundle unpacker/packer %s" % version)
		print("by DGIorio")
		print()
		print("Usage: python %s [option] <game> <input_file> <output_dir> <output_name>" % (sys.argv[0]))
		print()
		print("Options:")
		print("  -h, --help      Show this help message")
		print("  -v, --version   Show the tool version")
		print("  -u, --unpack    Unpack an given bundle file to the specified output directory")
		print("  -p, --pack      Pack an given resource table to the specified output directory and name it with the specified output name")
		print()
		print("Other input data:")
		print("       <game>     The game the file is from/to: BP or MW")
		print(" <input_file>     Input file or directory path")
		print(" <output_dir>     Output directory")
		print("<output_name>     Output file name, only for -p and --pack option")
		print()
	
	elif command == "-v" or command == "--version":
		print(version)
	
	elif command == "-u" or command == "--unpack":
		game = input("Source game:\n").strip()
		while game.lower() not in ["bp", "mw"]:
			game = input("Select one of the following games: BP or MW:\n")
		input_arg = os.path.abspath(input("File or folder to unpack:\n").replace('"', ''))
		output_dir = input("Output directory:\n").replace('"','')
		
		if os.path.isfile(output_dir):
			print("Error: invalid argument. <output_dir> must be an directory")
			return 1
		
		if os.path.isfile(input_arg):
			print("")
			if game.lower() == "bp":
				status = unpack_bundle(input_arg, output_dir, "IDs_" + os.path.basename(input_arg))
			elif game.lower() == "mw":
				status = unpack_bundle_mw(input_arg, output_dir, "IDs_" + os.path.basename(input_arg))
			print("Info: finished unpacking file")
		elif os.path.isdir(input_arg):
			unpack_to_same_folder = bool(int(input("Output to the same directory (1 for yes, 0 for no):\n")))
			print("")
			status = unpack_multiple_bundles(input_arg, output_dir, game, unpack_to_same_folder)
			print("Info: finished unpacking files")
	
	elif command == "-p" or command == "--pack":
		game = input("Target game:\n").strip()
		while game.lower() not in ["bp", "mw"]:
			game = input("Select one of the following games: BP or MW:\n")
		input_arg = os.path.abspath(input("File or folder to pack:\n").replace('"', ''))
		output_dir = input("Output directory:\n").replace('"','')
		output_name = input("Output file name with extension:\n")
		print("")
		
		if os.path.isfile(output_dir):
			print("Error: invalid argument. <output_dir> must be an directory")
			return 1
		
		if os.path.isfile(input_arg):
			if game.lower() == "bp":
				status = pack_bundle(input_arg, output_dir, output_name)
			elif game.lower() == "mw":
				status = pack_bundle_mw(input_arg, output_dir, output_name)
			print("Info: finished packing file")
		elif os.path.isdir(input_arg):
			#status = pack_multiple_bundles(input_arg, output_dir, output_name)
			print("Error: packing multiple bundles is not supporter yet")
			return 1
	else:
		print("Error: invalid argument. Please use the argument -h for help")
		return 1
	
	return 0


if __name__ == "__main__":
	try:
		input = raw_input
	except NameError:
		pass
	
	if len(sys.argv) == 1:
		print()
		print("Criterion's games bundle unpacker/packer %s" % version)
		print("by DGIorio")
		print()
		print("Command-line usage: python %s [option] <game> <input_file> <output_dir> <output_name>" % (sys.argv[0]))
		print()
		print("Options:")
		print("  -h, --help      Show this help message")
		print("  -v, --version   Show the tool version")
		print("  -u, --unpack    Unpack an given bundle file to the specified output directory")
		print("  -p, --pack      Pack an given resource table to the specified output directory and name it with the specified output name")
		print()
		print("When requested insert the input data")
		command = input("Option:\n")
		status = manual_command_handler(command.lower())
	
	elif sys.argv[1] == "-h" or sys.argv[1] == "--help":
		print()
		print("Criterion's games bundle unpacker/packer %s" % version)
		print("by DGIorio")
		print()
		print("Usage: python %s [option] <game> <input_file> <output_dir> <output_name>" % (sys.argv[0]))
		print()
		print("Options:")
		print("  -h, --help      Show this help message")
		print("  -v, --version   Show the tool version")
		print("  -u, --unpack    Unpack an given bundle file to the specified output directory")
		print("  -p, --pack      Pack an given resource table to the specified output directory and name it with the specified output name")
		print()
		print("Other input data:")
		print("       <game>     The game the file is from/to: BP or MW")
		print(" <input_file>     Input file or directory path")
		print(" <output_dir>     Output directory")
		print("<output_name>     Output file name, only for -p and --pack option")
		print()
	
	elif sys.argv[1] == "-v" or sys.argv[1] == "--version":
		print(version)
	
	elif sys.argv[1] == "-u" or sys.argv[1] == "--unpack":
		if len(sys.argv)-1 != 4:
			print("Error: insuficient arguments. You must specify the source game (BP or MW), an input file and an output directory")
		elif os.path.isfile(sys.argv[4]):
			print("Error: invalid argument. <output_dir> must be an directory")
		else:
			if os.path.isfile(sys.argv[3]):
				if sys.argv[2].lower() == "bp":
					status = unpack_bundle(sys.argv[3], sys.argv[4], "IDs_" + os.path.basename(sys.argv[3]))
				elif sys.argv[2].lower() == "mw":
					status = unpack_bundle_mw(sys.argv[3], sys.argv[4], "IDs_" + os.path.basename(sys.argv[3]))
				print("Info: finished unpacking file")
			elif os.path.isdir(sys.argv[3]):
				status = unpack_multiple_bundles(sys.argv[3], sys.argv[2], sys.argv[4])
				print("Info: finished unpacking files")
	
	elif sys.argv[1] == "-p" or sys.argv[1] == "--pack":
		if len(sys.argv)-1 != 5:
			print("Error: insuficient arguments. You must specify a target game (BP or MW), an input file, an output directory and an output file name")
		elif os.path.isfile(sys.argv[4]):
			print("Error: invalid argument. <output_dir> must be an directory")
		else:
			if os.path.isfile(sys.argv[3]):
				if sys.argv[2].lower() == "bp":
					status = pack_bundle(sys.argv[3], sys.argv[4], sys.argv[5])
				elif sys.argv[2].lower() == "mw":
					status = pack_bundle_mw(sys.argv[3], sys.argv[4], sys.argv[5])
				print("Info: finished packing file")
			elif os.path.isdir(sys.argv[3]):
				#status = pack_multiple_bundles(sys.argv[3], sys.argv[4], sys.argv[5])
				print("Error: packing multiple bundles is not supporter yet")
	else:
		print("Error: invalid argument. Please use the argument -h for help")
