"""



"""
# In[1]: Imports

import os
import re
from skimage.transform import resize, rescale
from matplotlib import pyplot
import matplotlib.pyplot as plt
import numpy as np
from multiprocessing import Pool
np.random.seed(0)
import pydot
import graphviz
from keras.utils.vis_utils import plot_model
from tensorflow.keras.layers import Input, Dense, Conv2D, Conv2DTranspose, MaxPooling2D, Dropout, Flatten
from tensorflow.keras.layers import Conv2DTranspose, UpSampling2D, add
from tensorflow.keras.models import Model
from tensorflow.keras import regularizers
from tensorflow.keras import backend
import tensorflow as tf
print(tf.__version__)

# In[2]: Building Encoder


#Lets design the Encoder for the Autoencoder
#We will use the Functional API

#Input layer will be 256x256x3 (3 RGB channels as image depth)
input_img = Input(shape = (256, 256, 3)) #Using Input class from Keras

#Activity regularizer will regularize the output after activation.
#64 3by3 filters with same padding
layer1 = Conv2D(64, (3, 3), padding = 'same', 
                activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(input_img) #applied to the input image 

layer2 = Conv2D(64, (3, 3), padding = 'same', 
                activation = 'elu', kernel_initializer='he_normal',
                activity_regularizer = regularizers.l1(10e-10))(layer1) #applied to the output of layer1 

#Downscaling picture dimensions with scale factor of 2 using MaxPool2D
layer3 = MaxPooling2D(padding = 'same')(layer2) #Applied to layer 2 output

#To learn new features in the smaller 'space',
#We need a bigger convolutional layer to make up for losing information due to the smaller space
layer4 = Conv2D(128, (3,3), padding = 'same', 
                activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(layer3) #applied to the output of layer3 

layer5 = Conv2D(128, (3,3), padding = 'same', 
                activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(layer4) #applied to the output of layer4 

#Downscaling picture dimensions with scale factor of 2 using MaxPool2D
layer6 = MaxPooling2D(padding = 'same')(layer5) #Applied to layer5 output

#The depth of the encoder can be adjusted but so far it is deep enough relevant to the input
#Last encoder layer with more filters to make up for the loss of information
layer7 = Conv2D(256, (3,3), padding = 'same',
                activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(layer6) #applied to the output of layer4 

#We will use the Model class from keras to put the model together
encoder = Model(input_img, layer7) 

#Lets see the encoder model summary
encoder.summary()

# In[3]: Building Decoder

#Now we need to do the reverse of Encoder for the decoder
layer8 = Conv2DTranspose(128, (3,3), strides = (2,2), padding = 'same',
               activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(layer7)

layer9 = Conv2D(128, (3,3), padding = 'same',
               activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(layer8)

#We create a merge layer between layer5 and layer10 to add their inputs
#Merging them helps to prevent the vanishing gradient by sharing information(such as weights)
layer10 = add([layer5, layer9]) #Merge layer between layer 5 and 10


layer11 = Conv2DTranspose(64, (3,3), strides = (2,2),  padding = 'same',
               activation = 'elu', kernel_initializer='he_normal', 
                activity_regularizer = regularizers.l1(10e-10))(layer10)

layer12 = Conv2D(64, (3,3), padding = 'same',
               activation = 'elu', kernel_initializer='he_normal', 
                 activity_regularizer = regularizers.l1(10e-10))(layer11)

layer13 = add([layer12, layer2])

#Lets create the decoder output. We need 3 neurons for 3 RGB channels
decoder = Conv2D(3, (3,3), padding = 'same',
               activation = 'elu', kernel_initializer='he_normal', 
               activity_regularizer = regularizers.l1(10e-10))(layer13)

#Lets combine the encoder and decoder to an Autoencoder using Model class
autoencoder = Model(input_img, decoder)

#Lets create a summary
autoencoder.summary()

# In[4]: Loss function DSSIMLOSS

def dssimloss(y_true, y_pred):
    ssim1 = tf.image.ssim(y_true, y_pred, 1.0)
    
    return backend.mean(1 - ssim1)

# In[5]: Define optimizer and compile Model Autoencoder


autoencoder.compile(optimizer = 'adadelta', loss = dssimloss)


# In[6]: #Load images and Define train loop

def train_batches():

    #Batch size
    batches = 256 
    
    #point in current batch
    batch = 0 
    
    #Current batch number
    batch_nb = 0 
    
    max_batches = -1 #No limit to number of batches
    
    #number of epochs
    epochs = 20 

    x_train = []
    x_train_down = []
    
    x_train_1 = [] #high-res image array for x_train
    x_train_down1 = [] #array for low-res copy x_train_down
    
    data_set_path = r"C:\Users\Desktop\Desktop\Artificial Intelligence Main\Projects\Super Res\Completed\data\rez\cars_train"
    
    for dirpath, dirnames, filenames in os.walk(data_set_path):
        
        for filename in filenames:
            if re.search("\.(jpg|jpeg|JPEG|png)$", filename):
                if batch_nb == max_batches: 
                    return x_train_1, x_train_down1
            
                filepath = os.path.join(dirpath, filename) #set path for each image
               
                image = pyplot.imread(filepath) #read image from path
                
                if len(image.shape) > 2:
                    
                    #Resizing images that are larger than 256,256 to be 256,256
                    image_resized = resize(image, (256, 256)) #resizing images
                    
                    x_train.append(image_resized) #adding resized image to x_train
                   
                    x_train_down.append(rescale(rescale(image_resized, 0.5, multichannel = True), 2.0, multichannel = True)) #downsampling resized image to low-res 
                   
                    batch += 1
                    
                    if batch == batches:
                        
                        batch_nb += 1

                        x_train_1 = np.array(x_train)
                        x_train_down1 = np.array(x_train_down)
                                              
                        print('Training batch', batch_nb, '(', batches, ')')

                        autoencoder.fit(x_train_down1, x_train_1, epochs = epochs, batch_size = 16, shuffle = True, validation_split = 0.20)
                    
                        x_train = []
                        x_train_down = []
                    
                        batch = 0

    return x_train_1, x_train_down1

# In[7]: Train the model

x_train, x_train_down = train_batches()



# In[8]: Save model and load it

autoencoder.save(r"C:\Users\Desktop\Desktop\Artificial Intelligence Main\Projects\Super Res\MyNetwork.h5")

autoencoder = tf.keras.models.load_model(r"C:\Users\Desktop\Desktop\Artificial Intelligence Main\Projects\Super Res\MyNetwork.h5")










