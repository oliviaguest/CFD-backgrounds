import os
import glob
from PIL import Image, ImageChops

import numpy as np
import pandas as pd
import ntpath

from directories import bg_dir, fg_dir, stimuli_dir, cropped_dir


def trim(im):
    """Takes an image object and trims all the contiguous space around the
    edges."""
    # https://stackoverflow.com/a/48605963/3433914
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)

    # If the image is completely empty, this method returns None.
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


def pixel_ratio(im):
    """Takes an image object and returns the ratio of the number of pixels that
    have exactly 255 in the alpha channel and all the pixels."""
    pixels = list(im.getdata())
    count = 0
    # Count the non-transparent pixels
    for i, pixel in enumerate(pixels):
        # if pixel[3] > 128:
        if pixel[3] == 255:
            count += 1
    return count / len(pixels)


def crop_backgrounds(bg_dir, cropped_dir, cropped='both'):
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

        if cropped == 'bottom':
            # Cropping from the bottom
            im_bottom = im.crop(
                (0, 0, im.width, im.height - crop_pixels))
            im_bottom.save(cropped_dir + ntpath.basename(file) +
                           '_cropped_bottom' + '.jpg')
            return (im_bottom.height, im_bottom.width)


        if cropped == 'top':
            # Cropping from the top
            im_top = im.crop((0,  crop_pixels, im.width, im.height))
            im_top.save(cropped_dir + ntpath.basename(file) +
                        '_cropped_top' + '.jpg')
            return (im_top.height, im_top.width)

        if cropped == 'both':
            # Cropping from both
            im_both = im.crop((0, crop_pixels_both, im.width, im.height -
                               crop_pixels_both))
            # This is here to stop any rounding errors with resizing
            im_both = im_both.resize((im_both.width, im_both.height))
            im_both.save(cropped_dir + ntpath.basename(file) +
                         '_cropped_both' + '.jpg')
            return (im_both.height, im_both.width)


def paste_image_on_background(fg_im, bg_im):
    """Takes a foreground image, places it on top of a background image, and
    returns the combined image and the pixel ratio of foreground to
    background."""
    fg_im = trim(fg_im)

    fg_im.thumbnail((bg_im.width, bg_im.height))

    pixels_to_center = int(np.round(bg_im.width - fg_im.width) / 2)
    fg_im = fg_im.crop(
        (-pixels_to_center, 0, bg_im.width - pixels_to_center, bg_im.height))
    assert fg_im.height == bg_im.height
    assert fg_im.width == bg_im.width
    bg_im.paste(fg_im, (0, 0), fg_im)

    return bg_im, pixel_ratio(fg_im)


if __name__ == "__main__":

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

            stim_im, ratio = paste_image_on_background(fg_im, bg_im)
            # print('Pixel ratio of face to background = ', ratio)
            # Directory to savr the output stimuli.
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
