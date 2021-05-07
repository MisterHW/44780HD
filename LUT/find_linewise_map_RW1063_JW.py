#!python3.8
from PIL import Image, ImageDraw
import operator
from typing import Callable


class tiled_character_map:
	img  = None 
	draw = None
	margin      = [0,0,0,0] # top, left, bottom, right
	tile_count  = [1,1]	
	tile_pitch  = [0,0]
	tile_offset = [0,0]
	tile_size   = [1,1]
	
	get_tile_pos_by_index: Callable[[int], list] = None
	
	def __del__(self):
		if self.img:
			del self.img 
		if self.draw:
			del self.draw
			
	def __init__(self, tile_count:[int,int], tile_pitch:[int,int], margin = [0,0,0,0]):
		self.tile_count = tile_count 
		self.tile_pitch = tile_pitch 
		self.margin = margin 
		# create an empty 8 bit monochrome bitmapimg
		width  = margin[1] + margin[3] + tile_count[0]*tile_pitch[0] 
		height = margin[0] + margin[2] + tile_count[1]*tile_pitch[1]  
		self.img = Image.new(
			mode='L', 
			size=[width , height]
			)
		self.draw = ImageDraw.Draw(self.img)
		self.draw.rectangle([(0,0),self.img.size], fill = (128) )
		
	def open(self, fn:str):
		if self.img:
			del self.img 
		if self.draw:
			del self.draw
			
		newimg  = Image.open(fn)
		if newimg.mode != 'L':
			self.img = newimg.convert(mode='L')
		else:
			self.img = newimg
			
		if self.img:
			self.draw =  ImageDraw.Draw(self.img)
		
	def get_aoi_origin(self, tile_pos:[int,int]):
		x = self.margin[1] + self.tile_offset[0] + (tile_pos[0] * self.tile_pitch[0])
		y = self.margin[0] + self.tile_offset[1] + (tile_pos[1] * self.tile_pitch[1])
		return [x,y]
			
	def fill_tile(self, tile_pos:[int,int], colour:int):
		[x1, y1] = self.get_aoi_origin(tile_pos)
		x2 = x1 + self.tile_size[0] - 1
		y2 = y1 + self.tile_size[1]	- 1
		self.draw.rectangle(
			[ (x1,y1) , (x2,y2) ], 
			fill = (colour) 
			)
			
	def pixels_to_word(self, pixel_start:[int,int], npixels:int, ref_color, big_endian:bool, shift:int=0):	
		word = 0
		b = 1 << shift
		x_range = range(0, npixels) if big_endian else range(npixels-1, -1, -1)
		for i in x_range:
			pixel_val = self.img.getpixel((pixel_start[0] + i, pixel_start[1]))
			word = word | ( b if pixel_val == ref_color else 0 )
			b = b << 1
		return word


if __name__ == "__main__":

	### set up a character mapimg and fill it with black rectangles
	mapimg = tiled_character_map([16,16], [6,9], [1,1,0,0]) 
	mapimg.tile_size = [5,8]
	mapimg.get_tile_pos_by_index = lambda idx, ts = mapimg.tile_count: [ (idx % (ts[0]*ts[1])) // ts[1] , idx % ts[1]] # assign tile organization function 
	
	for i in range( 16, 256 ):
		mapimg.fill_tile( mapimg.get_tile_pos_by_index(i), 0 )	
	
	mapimg.img.save('output/blank_layout.bmp')

	### load mapimg data
	mapimg.open('RW1063_JW.png')

	### TEST PATTERN: overwrite existing mapimg to check pixel alignment
	#	for y in range(1,5):
	#		for x in range(0 , mapimg.tile_count[0]):
	#			mapimg.fill_tile([x,y], 128)
	#	mapimg.img.save('output/ROI_alignment_test.bmp')
	#	exit()
	
	### convert pixel data to aligned bit representations
	# 	mapimg_data is a 2D array of arrays containing 1 bit pixel data. For example, the character 'A' will be represented as
	#	[ 	0b00000 ,
	#		0b00100 ,
	#		0b01010 ,
	#		0b10001 ,
	#		0b10001 ,
	#		0b11111 ,
	#		0b10001 ,
	#		0b10001 ]
	mapimg_data = [ [ 
				mapimg.pixels_to_word( list(map(operator.add, mapimg.get_aoi_origin(mapimg.get_tile_pos_by_index(idx)), [0,y])) , mapimg.tile_size[0] , (255), big_endian=False )
				  for y in range(0 , mapimg.tile_size[1])  
				] for idx in range(0 , 256)
				]
	#for idx in range(16 , 256):
	#		print(idx, '\t', mapimg_data[idx])	
			
			
	### create a LUT that visually represents 2^5=32 columns for all possible 5 bit states, and 8 rows for sequential rendering, one for each line in a character
	lutimg = tiled_character_map( [32,8] , [6,9], [0,1,0,0] ) 
	lutimg.tile_size = [5,8]
	
	lut_data = [[None for y in range(0,lutimg.tile_count[1])] for x in range(0,lutimg.tile_count[0])]
	
	### add hard-coded patch values
	# todo...
	

	### populate LUT with direct matches and visualize the choices 
	for v in range(0 , lutimg.tile_count[1]):
		for u in range( 0 , lutimg.tile_count[0] ):
			org = lutimg.get_aoi_origin([u,v])
			lutimg.fill_tile( [u,v] , 64 )
			
			# seek matches in a valid range of characters (0..15 are the 8 CGRAM chars repeated twice)
			for idx in range(8,256):
				if mapimg_data[idx][v] == u:
					lut_data[u][v] = idx
					break

			# copy-paste map character image to LUT image area
			if lut_data[u][v] is not None:
				src_aoi_org = mapimg.get_aoi_origin(mapimg.get_tile_pos_by_index(lut_data[u][v]))
				src_aoi = ( src_aoi_org[0], src_aoi_org[1], src_aoi_org[0] + mapimg.tile_size[0], src_aoi_org[1] + mapimg.tile_size[1] )
				character = mapimg.img.crop(src_aoi)
				lutimg.img.paste(character, lutimg.get_aoi_origin([u,v]))
			
			# overlay relevant pixels
			for x in range( 0 , lutimg.tile_size[0] ):
				pixel_col = (192) if (u & (1 << (lutimg.tile_size[0] - 1 - x))) else (0) 
				lutimg.img.putpixel( (org[0]+x, org[1]+v) , pixel_col ) 
	
	lutimg.img.save('output/lutimg_bit_patterns.bmp')
				
				
	### save LUT data (character codes)
	f = open('output/LUT.txt', 'w')
	for v in range(0, lutimg.tile_count[1]):
		for u in range(0 , mapimg.tile_count[0]):
			f.write(repr(lut_data[u][v]) + '\t')
		f.write('\n')
	f.close()		
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				
				


