#
# The SELDnet architecture
#

from keras.layers import Bidirectional, Conv2D, MaxPooling2D, Input, MaxPooling3D, Conv3D, merge
from keras.layers.core import Dense, Activation, Dropout, Reshape, Permute
from keras.layers.recurrent import GRU
from keras.layers.normalization import BatchNormalization
from keras.models import Model, load_model
from keras.layers.wrappers import TimeDistributed
from keras.optimizers import Adam
import keras
from keras_self_attention import SeqSelfAttention

keras.backend.set_image_data_format('channels_first')
from IPython import embed


def get_model(data_in, data_out, dropout_rate, nb_cnn2d_filt, pool_size,
                                rnn_size, fnn_size, classification_mode, weights, loader, loader2):
    # model definition
    spec_start = Input(shape=(data_in[-3], data_in[-2], data_in[-1]))
    spec_cnn = spec_start
    for i, convCnt in enumerate(pool_size):
        spec_cnn = Conv2D(filters=nb_cnn2d_filt, kernel_size=(3, 3), padding='same')(spec_cnn)
        spec_cnn = BatchNormalization()(spec_cnn)
        spec_cnn = Activation('relu')(spec_cnn)
        spec_cnn = MaxPooling2D(pool_size=(1, pool_size[i]))(spec_cnn)
        spec_cnn = Dropout(dropout_rate)(spec_cnn)
    spec_cnn = Permute((2, 1, 3))(spec_cnn)

    spec_rnn = Reshape((data_in[-2], -1))(spec_cnn)
    for nb_rnn_filt in rnn_size:
        spec_rnn = Bidirectional(
            GRU(nb_rnn_filt, activation='tanh', dropout=dropout_rate, recurrent_dropout=dropout_rate,
                return_sequences=True),
            merge_mode='mul'
        )(spec_rnn)

    # Attention
    # spec_rnn = SeqSelfAttention(attention_activation='tanh')(spec_rnn)

    # DOA
    doa = spec_rnn
    # doa = SeqSelfAttention(attention_activation='tanh')(spec_rnn)
    for nb_fnn_filt in fnn_size:
        doa = TimeDistributed(Dense(nb_fnn_filt))(doa)
        doa = Dropout(dropout_rate)(doa)

    doa = TimeDistributed(Dense(data_out[1][-1]))(doa)
    doa = Activation('tanh', name='doa_out')(doa)

    # SED
    sed = spec_rnn
    # sed = SeqSelfAttention(attention_activation='tanh')(spec_rnn)
    for nb_fnn_filt in fnn_size:
        sed = TimeDistributed(Dense(nb_fnn_filt))(sed)
        sed = Dropout(dropout_rate)(sed)

    sed = TimeDistributed(Dense(data_out[0][-1]))(sed)
    sed = Activation('sigmoid', name='sed_out')(sed)

    model = Model(inputs=spec_start, outputs=[sed, doa])
    if loader:
        model = load_model('C:/Users/shalea2/PycharmProjects/Drones/models/attention_3_ansim_ov1_split2_regr0_3d0_1_model.h5', custom_objects=SeqSelfAttention.get_custom_objects())
        if loader2:
            temp_weights = [layer.get_weights() for layer in model.layers]
            model.layers.pop()
            model.layers.pop()
            model.layers.pop()
            model.layers.pop()
            doa = TimeDistributed(Dense(data_out[1][-1]))(model.layers[-1].output)
            doa = Activation('tanh', name='doa_out')(doa)
            sed = TimeDistributed(Dense(data_out[0][-1]))(model.layers[-2].output)
            sed = Activation('sigmoid', name='sed_out')(sed)
            model = Model(inputs=model.get_input_at(0), outputs=[sed, doa])
            for i in range(len(temp_weights)-4):
                model.layers[i].set_weights(temp_weights[i])
    model.compile(optimizer=Adam(), loss=['binary_crossentropy', 'mse'], loss_weights=weights)

    model.summary()
    return model
