import tensorflow as tf
from tensorflow.contrib.rnn import GRUCell, LSTMBlockCell


def postnet(inputs, layers, conv_width, channels, is_training):
    x = inputs
    with tf.variable_scope('decoder_postnet'):
        for i in range(layers):
            activation = tf.nn.tanh if i < layers - 1 else None
            x = conv1d(x, conv_width, channels, activation, is_training, 'postnet_conv_%d' % i)
    return tf.layers.dense(x, inputs.shape[2])  # Project to input shape


def prenet(inputs, is_training, layer_sizes, scope=None):
    x = inputs
    drop_rate = 0.5 if is_training else 0.0
    with tf.variable_scope(scope or 'prenet'):
        for i, size in enumerate(layer_sizes):
            dense = tf.layers.dense(x, units=size, activation=tf.nn.relu, name='dense_%d' % (i + 1))
            x = tf.layers.dropout(dense, rate=drop_rate, training=is_training, name='dropout_%d' % (i + 1))
    return x


def conv_and_gru(inputs, input_lengths, conv_layers, conv_width, conv_channels,
                 gru_units_unidirectional, is_training, scope):
    with tf.variable_scope(scope):
        # convolutional layers
        convolved_inputs = inputs

        for i in range(conv_layers):
            activation = tf.nn.relu if i < conv_layers - 1 else None
            convolved_inputs = conv1d(convolved_inputs, conv_width,
                                      conv_channels, activation, is_training, 'conv_{}'.format(i))

        # bidirectional GRU
        outputs, states = tf.nn.bidirectional_dynamic_rnn(
            GRUCell(gru_units_unidirectional),
            GRUCell(gru_units_unidirectional),
            convolved_inputs,
            sequence_length=input_lengths,
            dtype=tf.float32,
            scope='{}_gru'.format(scope))

        # concatenate forwards and backwards
        return tf.concat(outputs, axis=2)

def conv_and_lstm(inputs, input_lengths, conv_layers, conv_width, conv_channels,
                 lstm_units_unidirectional, is_training, scope):
    with tf.variable_scope(scope):
        # convolutional layers
        convolved_inputs = inputs

        for i in range(conv_layers):
            activation = tf.nn.relu if i < conv_layers - 1 else None
            convolved_inputs = conv1d(convolved_inputs, conv_width,
                                      conv_channels, activation, is_training, 'conv_{}'.format(i))

        # bidirectional LSTM
        outputs, states = tf.nn.bidirectional_dynamic_rnn(
            LSTMBlockCell(lstm_units_unidirectional),
            LSTMBlockCell(lstm_units_unidirectional),
            convolved_inputs,
            sequence_length=input_lengths,
            dtype=tf.float32,
            scope='{}_lstm'.format(scope))

        # concatenate forwards and backwards
        return tf.concat(outputs, axis=2)


def encoder_cbhg(inputs, input_lengths, is_training, depth):
    input_channels = inputs.get_shape()[2]
    return cbhg(
        inputs,
        input_lengths,
        is_training,
        scope='encoder_cbhg',
        K=16,
        projections=[128, input_channels],
        depth=depth)


def post_cbhg(inputs, input_dim, is_training, depth):
    return cbhg(
        inputs,
        None,
        is_training,
        scope='post_cbhg',
        K=8,
        projections=[256, input_dim],
        depth=depth)


def cbhg(inputs, input_lengths, is_training, scope, K, projections, depth):
    with tf.variable_scope(scope):
        with tf.variable_scope('conv_bank'):
            # Convolution bank: concatenate on the last axis to stack channels from all convolutions
            conv_outputs = tf.concat(
                [conv1d(inputs, k, 128, tf.nn.relu, is_training, 'conv1d_%d' % k) for k in range(1, K + 1)],
                axis=-1
            )

        # Maxpooling:
        maxpool_output = tf.layers.max_pooling1d(
            conv_outputs,
            pool_size=2,
            strides=1,
            padding='same')

        # Two projection layers:
        proj1_output = conv1d(maxpool_output, 3, projections[0], tf.nn.relu, is_training, 'proj_1')
        proj2_output = conv1d(proj1_output, 3, projections[1], None, is_training, 'proj_2')

        # Residual connection:
        highway_input = proj2_output + inputs

        half_depth = depth // 2
        assert half_depth * 2 == depth, 'encoder and postnet depths must be even.'

        # Handle dimensionality mismatch:
        if highway_input.shape[2] != half_depth:
            highway_input = tf.layers.dense(highway_input, half_depth)

        # 4-layer HighwayNet:
        for i in range(4):
            highway_input = highwaynet(highway_input, 'highway_%d' % (i + 1), half_depth)
        rnn_input = highway_input

        # Bidirectional RNN
        outputs, states = tf.nn.bidirectional_dynamic_rnn(
            GRUCell(half_depth),
            GRUCell(half_depth),
            rnn_input,
            sequence_length=input_lengths,
            dtype=tf.float32)
        return tf.concat(outputs, axis=2)  # Concat forward and backward


def highwaynet(inputs, scope, depth):
    with tf.variable_scope(scope):
        H = tf.layers.dense(
            inputs,
            units=depth,
            activation=tf.nn.relu,
            name='H')
        T = tf.layers.dense(
            inputs,
            units=depth,
            activation=tf.nn.sigmoid,
            name='T',
            bias_initializer=tf.constant_initializer(-1.0))
        return H * T + inputs * (1.0 - T)


def conv1d(inputs, kernel_size, channels, activation, is_training, scope):
    with tf.variable_scope(scope):
        conv1d_output = tf.layers.conv1d(
            inputs,
            filters=channels,
            kernel_size=kernel_size,
            activation=activation,
            padding='same')
        return tf.layers.batch_normalization(conv1d_output, training=is_training)
