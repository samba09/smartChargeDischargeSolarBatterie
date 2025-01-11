
from PIL import Image
import math
import gzip

def convertImage(path):
    # open method used to open different extension image file
    im = Image.open(path + "/4_7_inch_plot.png")
  
    
    # convert to grayscale
    im = im.convert(mode='L')
    width, height = im.size
    if (width > 960):
        area = ((width-960) / 2, (height - 540)/2, (width-960) / 2+960, (height - 540)/2+540)
        print(area)
        im = im.crop(area)
    print(im.size)
    #im.show()

    # Write out the output file.
    with open(path + "/4_7_inch_plot.raw", 'wb') as f:
        #f.write("960")
        #f.write("540")
        #f.write(
        #    "const uint8_t {}_data[({}*{})/2] = {{\n".format("tibber", math.ceil(im.size[0] / 2) * 2, im.size[1])
        #)
        for y in range(0, im.size[1]):
            byte = 0
            for x in range(0, im.size[0]):
                l = im.getpixel((x, y))
                if x % 2 == 0:
                    byte = l >> 4

                else:
                    byte |= l & 0xF0
                    f.write(bytes([byte]))


if __name__ == '__main__':
    convertImage("temp_data")

