
# coding: utf-8

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
import random
import pathlib

import tensorflow as tf

from tensorflow.keras.models import Sequential
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
# The training dataset consists of 2000 images of dogs and cats, split
# in half.  In addition, the validation set consists of 1000 images,

if 'DATADIR' in os.environ:
    DATADIR = os.environ['DATADIR']
else:
    DATADIR = "/scratch/project_2000859/extracted/"

datapath = os.path.join(DATADIR, "dogs-vs-cats/train-2000/tfrecord/")

nimages = dict()
nimages['train'] = 2000
nimages['validation'] = 1000

# ### Data augmentation
# 
# We need to resize all training and validation images to a fixed
# size. Here we'll use 160x160 pixels.
# 
# Then, to make the most of our limited number of training examples,
# we'll apply random transformations (crop and horizontal flip) to
# them each time we are looping over them. This way, we "augment" our
# training dataset to contain more data. There are various
# transformations readily available in TensorFlow, see tf.image
# (https://www.tensorflow.org/versions/r2.0/api_docs/python/tf/image)
# for more information.

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
# Let's now define our TF Datasets
# (https://www.tensorflow.org/versions/r2.0/api_docs/python/tf/data/Dataset#class_dataset)
# for training and validation data. We use the TFRecordDataset
# (https://www.tensorflow.org/versions/r2.0/api_docs/python/tf/data/TFRecordDataset)
# class, which reads the data records from multiple TFRecord files.

train_filenames = [datapath+"train-{0:05d}-of-00004".format(i)
                   for i in range(4)]
train_dataset = tf.data.TFRecordDataset(train_filenames)

validation_filenames = [datapath+"validation-{0:05d}-of-00002".format(i)
                        for i in range(2)]
validation_dataset = tf.data.TFRecordDataset(validation_filenames)

# We then map() the TFRecord examples to the actual image data and
# decode the images.  Note that we shuffle and augment only the
# training data.

BATCH_SIZE = 32

train_dataset = train_dataset.map(parse_and_augment_image, num_parallel_calls=10)
train_dataset = train_dataset.shuffle(2000).batch(BATCH_SIZE, drop_remainder=True)
train_dataset = train_dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

validation_dataset = validation_dataset.map(parse_and_not_augment_image,
                                            num_parallel_calls=10)
validation_dataset = validation_dataset.batch(BATCH_SIZE, drop_remainder=True)
validation_dataset = validation_dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)

# ## Train a small CNN from scratch
# 
# Similarly as with MNIST digits, we can start from scratch and train
# a CNN for the classification task. However, due to the small number
# of training images, a large network will easily overfit, regardless
# of the data augmentation.
# 
# ### Initialization

model = Sequential()

model.add(Conv2D(32, (3, 3), input_shape=INPUT_IMAGE_SIZE, activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(32, (3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Conv2D(64, (3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))

model.add(Flatten())
model.add(Dense(64, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(1, activation='sigmoid'))

model.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

print(model.summary())

# ### Learning

# We'll use TensorBoard to visualize our progress during training.

logdir = os.path.join(os.getcwd(), "logs",
                      "dvc_tfr-cnn-simple-"+datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
print('TensorBoard log directory:', logdir)
os.makedirs(logdir)
callbacks = [TensorBoard(log_dir=logdir)]

epochs = 20

history = model.fit(train_dataset, epochs=epochs,
                    validation_data=validation_dataset,
                    callbacks=callbacks, verbose=2)

fname = "dvc_tfr-cnn-simple.h5"
print('Saving model to', fname)
model.save(fname)
