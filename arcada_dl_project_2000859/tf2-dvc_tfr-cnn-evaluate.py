# # Dogs-vs-cats classification with CNNs
# 
# In this notebook, we'll train a convolutional neural network (CNN,
# ConvNet) to classify images of dogs from images of cats using
# TensorFlow 2.0 / Keras. This notebook is largely based on the blog
# post [Building powerful image classification models using very
# little data]
# (https://blog.keras.io/building-powerful-image-classification-models-using-very-little-data.html)
# by François Chollet.
# 
# **Note that using a GPU with this notebook is highly recommended.**
# 
# First, the needed imports.

import os
# 0 = all messages are logged (default behavior)
# 1 = INFO messages are not printed
# 2 = INFO and WARNING messages are not printed
# 3 = INFO, WARNING, and ERROR messages are not printed
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import datetime
import sys
import random
import pathlib

import tensorflow as tf

from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import (Dense, Activation, Dropout, Conv2D,
                                    Flatten, MaxPooling2D, InputLayer)
from tensorflow.keras.preprocessing.image import (ImageDataGenerator, 
                                                  array_to_img, 
                                                  img_to_array, load_img)
from tensorflow.keras import applications, optimizers

from tensorflow.keras.callbacks import TensorBoard

import numpy as np

print('Using Tensorflow version:', tf.__version__,
      'Keras version:', tf.keras.__version__,
      'backend:', tf.keras.backend.backend())

# ## Data
# 
# The test set consists of 22000 images.

if 'DATADIR' in os.environ:
    DATADIR = os.environ['DATADIR']
else:
    DATADIR = "/scratch/project_2000859/extracted/"

datapath = os.path.join(DATADIR, "dogs-vs-cats/train-2000/tfrecord/")

nimages = dict()
nimages['test'] = 22000

# ### Data augmentation
# 
# We need to resize all test images to a fixed size. Here we'll use
# 160x160 pixels.
# 
# Unlike the training images, we do not apply any random
# transformations to the test images.

INPUT_IMAGE_SIZE = [160, 160, 3]

def preprocess_image(image, augment):
    image = tf.image.decode_jpeg(image, channels=3)
    if augment:
        image = tf.image.resize(image, [256, 256])
        image = tf.image.random_crop(image, INPUT_IMAGE_SIZE)
        image = tf.image.random_flip_left_right(image)
    else:
        image = tf.image.resize(image, INPUT_IMAGE_SIZE[:2])
    image /= 255.0  # normalize to [0,1] range
    return image

feature_description = {
    "image/encoded": tf.io.FixedLenFeature((), tf.string, default_value=""),
    "image/height": tf.io.FixedLenFeature((), tf.int64, default_value=0),
    "image/width": tf.io.FixedLenFeature((), tf.int64, default_value=0),
    "image/colorspace": tf.io.FixedLenFeature((), tf.string, default_value=""),
    "image/channels": tf.io.FixedLenFeature((), tf.int64, default_value=0),
    "image/format": tf.io.FixedLenFeature((), tf.string, default_value=""),
    "image/filename": tf.io.FixedLenFeature((), tf.string, default_value=""),
    "image/class/label": tf.io.FixedLenFeature((), tf.int64, default_value=0),
    "image/class/text": tf.io.FixedLenFeature((), tf.string, default_value="")}

def parse_and_augment_image(example_proto):
    ex = tf.io.parse_single_example(example_proto, feature_description)
    return (preprocess_image(ex["image/encoded"], True),
            ex["image/class/label"]-1)

def parse_and_not_augment_image(example_proto):
    ex = tf.io.parse_single_example(example_proto, feature_description)
    return (preprocess_image(ex["image/encoded"], False),
            ex["image/class/label"]-1)

# ### TF Datasets
# 
# Let's now define our TF Dataset
# (https://www.tensorflow.org/versions/r2.0/api_docs/python/tf/data/Dataset#class_dataset)
# for the test data. We use the TFRecordDataset
# (https://www.tensorflow.org/versions/r2.0/api_docs/python/tf/data/TFRecordDataset)
# class, which reads the data records from multiple TFRecord files.

test_filenames = [datapath+"test-{0:05d}-of-00022".format(i)
                   for i in range(22)]
test_dataset = tf.data.TFRecordDataset(test_filenames)

# We then map() the TFRecord examples to the actual image data and
# decode the images.

BATCH_SIZE = 32

test_dataset = test_dataset.map(parse_and_not_augment_image, num_parallel_calls=10)
test_dataset = test_dataset.batch(BATCH_SIZE, drop_remainder=False)
test_dataset = test_dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

# ### Initialization

if len(sys.argv)<2:
    print('ERROR: model file missing')
    sys.exit()
    
model = load_model(sys.argv[1])

print(model.summary())

# ### Inference

print('Evaluating model', sys.argv[1])
scores = model.evaluate(test_dataset, verbose=2)
print("Test set %s: %.2f%%" % (model.metrics_names[1], scores[1]*100))
