#Autor: Guilherme SalomÃ£o Agostini 
#Email: guime.sa9@gmail.com
#Referecias importantes:
    #https://keras.io/examples/vision/oxford_pets_image_segmentation/
    #https://towardsdatascience.com/a-comprehensive-introduction-to-different-types-of-convolutions-in-deep-learning-669281e58215
    #https://keras.io/api/layers/reshaping_layers/up_sampling2d/

#Teste usando uma rede porqueira montada por mim mesmo kkkk

#%% Prepare paths of input images and target segmentation masks
import os


input_dir = "/home/salomao/Desktop/semantic_segmentation-dogs-cats/images/"
target_dir = "/home/salomao/Desktop/semantic_segmentation-dogs-cats/annotations/trimaps/"
img_size = (160, 160)
num_classes = 4
batch_size = 32

input_img_paths = sorted( #Se o final for .png, ele pega e salva em uma lista, o endereÃ§o das imagens
    [
        os.path.join(input_dir, fname)
        for fname in os.listdir(input_dir)
        if fname.endswith(".jpg")
    ]
)
target_img_paths = sorted(  #Se o final for .png, ele pega e salva em uma lista, o endereÃ§o das imagens
    [
        os.path.join(target_dir, fname)
        for fname in os.listdir(target_dir)
        if fname.endswith(".png") and not fname.startswith(".")
    ]
)

print("Number of samples:", len(input_img_paths))

for input_path, target_path in zip(input_img_paths[:10], target_img_paths[:10]):
    print(input_path, "|", target_path) #Para confirmar se as imagens estao casadas pelo nome.

#%% What does one input image and corresponding segmentation mask look like?

from IPython.display import Image, display
from tensorflow.keras.preprocessing.image import load_img
import PIL #pillow
from PIL import ImageOps #Se nao tiver, ele fala que nao existe!!! BIZARRO

# Display input image #7
display(Image(filename=input_img_paths[9])) #printa a foto de um bexano -> imagem original dada um path

# Display auto-contrast version of corresponding target (per-pixel categories)
img = PIL.ImageOps.autocontrast(load_img(target_img_paths[9]))#load_img gera um objeto reconhecido pelo computador como "imagem"(interessante), loada a matriz imagem, em suma. O autocontrast, gera o maximo de contraste possivel, na imagem.
display(img)#display method, usado diretamente com a matriz, plota a imagem



#%% Prepare Sequence class to load & vectorize batches of data

from tensorflow import keras
import numpy as np


class OxfordPets(keras.utils.Sequence): #Objeto para tratar as imagens das classes e das etiquetas, criando os batch
    """Helper to iterate over the data (as Numpy arrays)."""

    def __init__(self, batch_size, img_size, input_img_paths, target_img_paths): #InformaÃ§Ãµes para o treinamento....
        self.batch_size = batch_size
        self.img_size = img_size
        self.input_img_paths = input_img_paths
        self.target_img_paths = target_img_paths

    def __len__(self): #retorna o comprimento do nosso dataset
        return len(self.target_img_paths) // self.batch_size #Quantos batchs, arredondado para baixo, existem.

    def __getitem__(self, idx): #Retorna uma tupla com a imagem RGB e a imagem anotada correspondente //  idx Ã© o index do batch
        """Returns tuple (input, target) correspond to batch #idx."""
        i = idx * self.batch_size #i Ã© o indice real da imagem em relacao ao batch
        batch_input_img_paths = self.input_img_paths[i : i + self.batch_size]#Coleto o batch todo
        batch_target_img_paths = self.target_img_paths[i : i + self.batch_size]#Coleto o batch todo
        x = np.zeros((batch_size,) + self.img_size + (3,), dtype="float32") #Monta um numpy vazio com o tamanho do batch e o tamanho da imagem em 3 canais
        for j, path in enumerate(batch_input_img_paths): #preencho as  imagens
            img = load_img(path, target_size=self.img_size)
            x[j] = img #preenchemos o esqueleto
        y = np.zeros((batch_size,) + self.img_size + (1,), dtype="uint8")#Monta um numpy vazio com o tamanho do batch e o tamanho da imagem em 1 canal (channels)
        for j, path in enumerate(batch_target_img_paths):
            img = load_img(path, target_size=self.img_size, color_mode="grayscale")#Para nao criar 3 canais, lemos como "grayscale"
            y[j] = np.expand_dims(img, 2) #Expando mais um canal (se nao, nao funciona kkk, sei la)
        return x, y

#%% Set aside a validation split

import random

# Split our img paths into a training and a validation set
val_samples = 1000
random.Random(1337).shuffle(input_img_paths)
random.Random(1337).shuffle(target_img_paths)
train_input_img_paths = input_img_paths[:-val_samples]
train_target_img_paths = target_img_paths[:-val_samples]
val_input_img_paths = input_img_paths[-val_samples:]
val_target_img_paths = target_img_paths[-val_samples:]

# Instantiate data Sequences for each split
train_gen = OxfordPets(
    batch_size, img_size, train_input_img_paths, train_target_img_paths
)
val_gen = OxfordPets(batch_size, img_size, val_input_img_paths, val_target_img_paths)




#%% Perpare U-Net Xception-style model

import tensorflow as tf
import keras

img_size = (160, 160)

#Input da rede 
layer_in = keras.layers.Input(shape= img_size + (3,))

x1 = keras.layers.Conv2D(8, kernel_size=3, padding='same', activation= 'relu')(layer_in)
x2  = keras.layers.MaxPool2D(pool_size=(2,2))(x1)

x3 = keras.layers.Conv2D(32, kernel_size=3, padding='same', activation= 'relu')(x2)
x4  = keras.layers.MaxPool2D(pool_size=(2,2))(x3)

x5 = keras.layers.Conv2D(128, kernel_size=3, padding='same', activation= 'relu')(x4)
x6  = keras.layers.MaxPool2D(pool_size=(2,2))(x5)



x7 = keras.layers.UpSampling2D(2)(x6)
x8 = keras.layers.Conv2DTranspose(128, kernel_size=3, padding="same", activation= 'relu')(x7)
x9 = keras.layers.add([x8,x5])

x10 = keras.layers.UpSampling2D(2)(x9)
x11 = keras.layers.Conv2DTranspose(32, kernel_size=3, padding="same", activation= 'relu')(x10)
x12 = keras.layers.add([x3,x11])

x13 = keras.layers.UpSampling2D(2)(x12)
x14 = keras.layers.Conv2DTranspose(1, kernel_size=3, padding="same", activation= 'relu')(x13)
x15 = keras.layers.add([x1,x14])

layer_out = keras.layers.Conv2DTranspose(4, kernel_size=3, activation="softmax", padding="same")(x15)
# Free up RAM in case the model definition cells were run multiple times
model = keras.models.Model(inputs=layer_in,outputs=layer_out)   
                         
#keras.backend.clear_session()

model_checkpoint_callback = [
    tf.keras.callbacks.ModelCheckpoint(
    filepath="/home/salomao/Desktop/CNN_try1_cleanlisses.h5",
    save_weights_only=False,
    monitor= "val_loss",
    mode='min',
    save_best_only=True)]


# Build model
model.summary()


#%% Train the model

# Configure the model for training.
# We use the "sparse" version of categorical_crossentropy
# because our target data is integers.
model.compile(optimizer="rmsprop", loss="sparse_categorical_crossentropy")


# Train the model, doing validation at the end of each epoch.
epochs = 15
model.fit(train_gen, epochs=epochs, validation_data=val_gen, verbose=1, callbacks=model_checkpoint_callback)


#%% Visualize predictions

# Generate predictions for all images in the validation set

val_gen = OxfordPets(batch_size, img_size, val_input_img_paths, val_target_img_paths)
val_preds = model.predict(val_gen)


def display_mask(i):
    """Quick utility to display a model's prediction."""
    mask = np.argmax(val_preds[i], axis=-1)
    mask = np.expand_dims(mask, axis=-1)
    img = PIL.ImageOps.autocontrast(keras.preprocessing.image.array_to_img(mask))
    display(img)

#%%
# Display results for validation image #10
i = 8

# Display input image
display(Image(filename=val_input_img_paths[i]))

# Display ground-truth target mask
img = PIL.ImageOps.autocontrast(load_img(val_target_img_paths[i]))
display(img)

# Display mask predicted by our model
display_mask(i)  # Note that the model only sees inputs at 150x150.





