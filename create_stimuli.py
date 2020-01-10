import os
import glob
from PIL import Image, ImageChops

import numpy as np
import pandas as pd
import ntpath
import argparse
from directories import bg_dir, fg_dir, stimuli_dir, cropped_dir
from utils import get_pixel_ratio

def trim(im):
    """Takes an image object and trims all the contiguous space around the
    edges."""
    # From: https://stackoverflow.com/a/48605963/3433914
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    # Bounding box given as a 4-tuple defining the left, upper, right, and
    # lower pixel coordinates.
    # If the image is completely empty, this method returns None.
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)



def crop_backgrounds(bg_dir, cropped_dir):
    """Normalise the backgrounds so they have the same size by cropping and
    resizing."""
    widths = []
    heights = []

    # Collect all widths and heights of all the background images to normalise
    # their sizes.
    for infile in glob.glob(bg_dir + "*.jp*g"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)
        widths.append(im.width)
        heights.append(im.height)

    # This is the final size we want the images to all be.
    size = (np.array(widths).min(), np.array(heights).max())

    # For each JPG image crop and save.
    for infile in glob.glob(bg_dir + "*.jp*g"):
        file, ext = os.path.splitext(infile)
        im = Image.open(infile)

        im.thumbnail(size, Image.ANTIALIAS)

        crop_pixels = np.round(im.height - np.array(heights).min())
        crop_pixels_both = int(crop_pixels / 2)

        try:
            os.makedirs(cropped_dir)
        except OSError:
            pass

        # Cropping from the bottom
        im_bottom = im.crop(
            (0, 0, im.width, im.height - crop_pixels))
        im_bottom.save(cropped_dir + ntpath.basename(file) +
                       '_cropped_bottom' + '.jpg')

        # Cropping from the top
        im_top = im.crop((0,  crop_pixels, im.width, im.height))
        im_top.save(cropped_dir + ntpath.basename(file) +
                    '_cropped_top' + '.jpg')

        # Cropping from both
        im_both = im.crop((0, crop_pixels_both, im.width, im.height -
                           crop_pixels_both))
        # This is here to stop any rounding errors with resizing.
        im_top = im_both.resize((im_top.width, im_top.height))
        im_both.save(cropped_dir + ntpath.basename(file) +
                     '_cropped_both' + '.jpg')
    return (im_top.height, im_top.width)


def paste_image_on_background(fg_im, bg_im, pixel_ratio=None):
    """Takes a foreground image, places it on top of a background image, and
    returns the combined image and the pixel ratio of foreground to
    background."""
    fg_im = trim(fg_im)
    fg_im.thumbnail((bg_im.width, bg_im.height))

    # If a pixel ratio is given, then we resize the foreground image.
    if pixel_ratio:

        pixels_to_center_x = int(np.round(bg_im.width - fg_im.width) / 2)
        pixels_to_bottom = bg_im.height - fg_im.height

        test_im = fg_im.crop((-pixels_to_center_x,
                              -pixels_to_bottom,
                              bg_im.width - pixels_to_center_x,
                              bg_im.height - pixels_to_bottom))
        # We need to know the current pixel ratio before we make the foreground
        # even smaller.
        current_pixel_ratio = get_pixel_ratio(test_im)

        # This is the number we need to get he desired ratio.
        diff_pixel_ratio = pixel_ratio / current_pixel_ratio

        # Check this ratio makes sense.
        if pixel_ratio > current_pixel_ratio:
            print('This pixel ratio means that the face is taller/wider than '
                  'the background.')
            exit()

        # Apply the transformation.
        fg_dims = (int(np.round((np.sqrt(diff_pixel_ratio) * fg_im.width))),
                   int(np.round((np.sqrt(diff_pixel_ratio) * fg_im.height))))
        fg_im = fg_im.resize(fg_dims)

    pixels_to_center_x = int(np.round(bg_im.width - fg_im.width) / 2)
    pixels_to_bottom = bg_im.height - fg_im.height

    # Calculate the placement of the foreground on the background.
    fg_im = fg_im.crop((-pixels_to_center_x,
                        -pixels_to_bottom,
                        bg_im.width - pixels_to_center_x,
                        bg_im.height - pixels_to_bottom))
    assert fg_im.height == bg_im.height
    assert fg_im.width == bg_im.width

    # And finally, paste one image onto the other.
    bg_im.paste(fg_im, (0, 0), fg_im)

    return bg_im, get_pixel_ratio(fg_im)


def main(desired_ratio):

    # Normalise the backgrounds.
    crop_backgrounds(bg_dir, cropped_dir)

    df = pd.DataFrame(
        columns=['Background', 'Foreground', 'Ratio', 'Filename'])

    # Iterate through the face images and place them on the backgrounds.
    for fg_infile in glob.glob(fg_dir + "*.png"):
        for bg_infile in glob.glob(cropped_dir + "*.jp*g"):
            bg_file, ext = os.path.splitext(bg_infile)

            bg_im = Image.open(bg_infile).convert('RGBA')

            fg_file, ext = os.path.splitext(fg_infile)
            fg_im = Image.open(fg_infile).convert('RGBA')

            stim_im, ratio = paste_image_on_background(fg_im, bg_im,
                                                       desired_ratio)

            # Directory to save the output stimuli.
            save_dir = stimuli_dir + ntpath.basename(bg_file) + '/'
            try:
                os.makedirs(save_dir)
            except OSError:
                pass
            save_filename = ntpath.basename(bg_file) + '_' + \
                ntpath.basename(fg_file) + '.jpg'

            df = df.append([{'Background': bg_file,
                             'Foreground': fg_file,
                             'Ratio': ratio,
                             'Filename': save_filename}])

            save_path = save_dir + save_filename
            print('Saving:', save_path)
            stim_im.convert('RGB').save(save_path)
    df.reset_index(drop=True).to_csv(stimuli_dir + 'stimuli.csv')


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Create the stimuli.')
    parser.add_argument("-r",
                        help="Desired pixel ratio for foreground/background.",
                        type=float, default='0.25')

    args = parser.parse_args()
    main(args.r)
