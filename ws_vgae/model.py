from fastgae.layers import *
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
flags = tf.app.flags
FLAGS = flags.FLAGS


class Model(object):
    """ Model base class"""
    def __init__(self, **kwargs):
        allowed_kwargs = {'name', 'logging'}
        for kwarg in kwargs.keys():
            assert kwarg in allowed_kwargs, 'Invalid keyword argument: ' + kwarg
        for kwarg in kwargs.keys():
            assert kwarg in allowed_kwargs, 'Invalid keyword argument: ' + kwarg
        name = kwargs.get('name')
        if not name:
            name = self.__class__.__name__.lower()
        self.name = name
        logging = kwargs.get('logging', False)
        self.logging = logging
        self.vars = {}

    def _build(self):
        raise NotImplementedError

    def build(self):
        """ Wrapper for _build() """
        with tf.variable_scope(self.name):
            self._build()
        variables = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope = self.name)
        self.vars = {var.name: var for var in variables}

    def fit(self):
        pass

    def predict(self):
        pass


#Note: this deterministic GAE model is not used in the paper.
class GCNModelAE(Model):
    """
    Standard Graph Autoencoder (GAE),
    with 2-layer GCN encoder and inner product decoder
    """
    def __init__(self, placeholders, num_features, features_nonzero, **kwargs):
        super(GCNModelAE, self).__init__(**kwargs)
        self.inputs = placeholders['features']
        self.input_dim = num_features
        self.features_nonzero = features_nonzero
        self.adj = placeholders['adj']
        self.dropout = placeholders['dropout']
        self.sampled_nodes = placeholders['sampled_nodes']
        self.build()

    def _build(self):
        self.hidden = GraphConvolutionSparse(input_dim = self.input_dim,
                                             output_dim = FLAGS.hidden,
                                             adj = self.adj,
                                             features_nonzero = self.features_nonzero,
                                             act = tf.nn.relu,
                                             dropout = self.dropout,
                                             logging = self.logging)(self.inputs)

        self.z_mean = GraphConvolution(input_dim = FLAGS.hidden,
                                       output_dim = FLAGS.dimension,
                                       adj = self.adj,
                                       act = lambda x: x,
                                       dropout = self.dropout,
                                       logging = self.logging)(self.hidden)

        self.reconstructions = InnerProductDecoder(fastgae = FLAGS.fastgae, # Whether to use FastGAE
                                                   sampled_nodes = self.sampled_nodes, # FastGAE subgraph
                                                   act = lambda x: x,
                                                   logging = self.logging)(self.z_mean)


class GCNModelVAE(Model):
    """
    VGAE with 2-layer GCN encoder, Gaussian distributions and inner product decoder,
    and WITH weight sharing
    """
    def __init__(self, placeholders, num_features, num_nodes, features_nonzero, **kwargs):
        super(GCNModelVAE, self).__init__(**kwargs)

        self.inputs = placeholders['features']
        self.input_dim = num_features
        self.features_nonzero = features_nonzero
        self.n_samples = num_nodes
        self.adj = placeholders['adj']
        self.dropout = placeholders['dropout']
        self.sampled_nodes = placeholders['sampled_nodes']
        self.build()

    def _build(self):
        self.hidden = GraphConvolutionSparse(input_dim = self.input_dim,
                                             output_dim = FLAGS.hidden,
                                             adj = self.adj,
                                             features_nonzero = self.features_nonzero,
                                             act = tf.nn.relu,
                                             dropout = self.dropout,
                                             logging = self.logging)(self.inputs)

        self.z_mean = GraphConvolution(input_dim = FLAGS.hidden,
                                       output_dim = FLAGS.dimension,
                                       adj = self.adj,
                                       act = lambda x: x,
                                       dropout = self.dropout,
                                       logging = self.logging)(self.hidden)

        self.z_log_std = GraphConvolution(input_dim = FLAGS.hidden,
                                          output_dim = FLAGS.dimension,
                                          adj = self.adj,
                                          act = lambda x: x,
                                          dropout = self.dropout,
                                          logging = self.logging)(self.hidden)

        self.z = self.z_mean + tf.random_normal([self.n_samples, FLAGS.dimension]) * tf.exp(self.z_log_std)

        self.reconstructions = InnerProductDecoder(fastgae = FLAGS.fastgae, # Whether to use FastGAE
                                                   sampled_nodes = self.sampled_nodes, # FastGAE subgraph
                                                   act = lambda x: x,
                                                   logging = self.logging)(self.z_mean)


class GCNModelVAENoWS(Model):
    """
    VGAE with 2-layer GCN encoder, Gaussian distributions and inner product decoder,
    but WITHOUT weight sharing
    """
    def __init__(self, placeholders, num_features, num_nodes, features_nonzero, **kwargs):
        super(GCNModelVAENoWS, self).__init__(**kwargs)

        self.inputs = placeholders['features']
        self.input_dim = num_features
        self.features_nonzero = features_nonzero
        self.n_samples = num_nodes
        self.adj = placeholders['adj']
        self.dropout = placeholders['dropout']
        self.sampled_nodes = placeholders['sampled_nodes']
        self.build()

    def _build(self):
        self.hidden_mean = GraphConvolutionSparse(input_dim = self.input_dim,
                                                  output_dim = FLAGS.hidden,
                                                  adj = self.adj,
                                                  features_nonzero = self.features_nonzero,
                                                  act = tf.nn.relu,
                                                  dropout = self.dropout,
                                                  logging = self.logging)(self.inputs)

        self.hidden_std = GraphConvolutionSparse(input_dim = self.input_dim,
                                                 output_dim = FLAGS.hidden,
                                                 adj = self.adj,
                                                 features_nonzero = self.features_nonzero,
                                                 act = tf.nn.relu,
                                                 dropout = self.dropout,
                                                 logging = self.logging)(self.inputs)

        self.z_mean = GraphConvolution(input_dim = FLAGS.hidden,
                                       output_dim = FLAGS.dimension,
                                       adj = self.adj,
                                       act = lambda x: x,
                                       dropout = self.dropout,
                                       logging = self.logging)(self.hidden_mean)

        self.z_log_std = GraphConvolution(input_dim = FLAGS.hidden,
                                          output_dim = FLAGS.dimension,
                                          adj = self.adj,
                                          act = lambda x: x,
                                          dropout = self.dropout,
                                          logging = self.logging)(self.hidden_std)

        self.z = self.z_mean + tf.random_normal([self.n_samples, FLAGS.dimension]) * tf.exp(self.z_log_std)

        self.reconstructions = InnerProductDecoder(fastgae = FLAGS.fastgae, # Whether to use FastGAE
                                                   sampled_nodes = self.sampled_nodes, # FastGAE subgraph
                                                   act = lambda x: x,
                                                   logging = self.logging)(self.z_mean)


class DeepGCNModelVAE(Model):
    """
    VGAE with 3-layer GCN encoder, Gaussian distributions and inner product decoder,
    and WITH weight sharing
    """
    def __init__(self, placeholders, num_features, num_nodes, features_nonzero, **kwargs):
        super(DeepGCNModelVAE, self).__init__(**kwargs)

        self.inputs = placeholders['features']
        self.input_dim = num_features
        self.features_nonzero = features_nonzero
        self.n_samples = num_nodes
        self.adj = placeholders['adj']
        self.dropout = placeholders['dropout']
        self.sampled_nodes = placeholders['sampled_nodes']
        self.build()

    def _build(self):       
        self.hidden1 = GraphConvolutionSparse(input_dim = self.input_dim,
                                              output_dim = FLAGS.hidden,
                                              adj = self.adj,
                                              features_nonzero = self.features_nonzero,
                                              act = tf.nn.relu,
                                              dropout = self.dropout,
                                              logging = self.logging)(self.inputs)

        self.hidden2 = GraphConvolution(input_dim = FLAGS.hidden,
                                        output_dim = FLAGS.hidden,
                                        adj = self.adj,
                                        act = lambda x: x,
                                        dropout = self.dropout,
                                        logging = self.logging)(self.hidden1)

        self.z_mean = GraphConvolution(input_dim = FLAGS.hidden,
                                       output_dim = FLAGS.dimension,
                                       adj = self.adj,
                                       act = lambda x: x,
                                       dropout = self.dropout,
                                       logging = self.logging)(self.hidden2)

        self.z_log_std = GraphConvolution(input_dim = FLAGS.hidden,
                                          output_dim = FLAGS.dimension,
                                          adj = self.adj,
                                          act = lambda x: x,
                                          dropout = self.dropout,
                                          logging = self.logging)(self.hidden2)

        self.z = self.z_mean + tf.random_normal([self.n_samples, FLAGS.dimension]) * tf.exp(self.z_log_std)

        self.reconstructions = InnerProductDecoder(fastgae = FLAGS.fastgae, # Whether to use FastGAE
                                                   sampled_nodes = self.sampled_nodes, # FastGAE subgraph
                                                   act = lambda x: x,
                                                   logging = self.logging)(self.z_mean)


class DeepGCNModelVAENoWS(Model):
    """
    VGAE with 3-layer GCN encoder, Gaussian distributions and inner product decoder,
    but WITHOUT weight sharing
    """
    def __init__(self, placeholders, num_features, num_nodes, features_nonzero, **kwargs):
        super(DeepGCNModelVAENoWS, self).__init__(**kwargs)

        self.inputs = placeholders['features']
        self.input_dim = num_features
        self.features_nonzero = features_nonzero
        self.n_samples = num_nodes
        self.adj = placeholders['adj']
        self.dropout = placeholders['dropout']
        self.sampled_nodes = placeholders['sampled_nodes']
        self.build()

    def _build(self):
        self.hidden1_mean = GraphConvolutionSparse(input_dim = self.input_dim,
                                                   output_dim = FLAGS.hidden,
                                                   adj = self.adj,
                                                   features_nonzero = self.features_nonzero,
                                                   act = tf.nn.relu,
                                                   dropout = self.dropout,
                                                   logging = self.logging)(self.inputs)

        self.hidden2_mean = GraphConvolution(input_dim = FLAGS.hidden,
                                             output_dim = FLAGS.hidden,
                                             adj = self.adj,
                                             act = lambda x: x,
                                             dropout = self.dropout,
                                             logging = self.logging)(self.hidden1_mean)
        
        self.hidden1_std = GraphConvolutionSparse(input_dim = self.input_dim,
                                                  output_dim = FLAGS.hidden,
                                                  adj = self.adj,
                                                  features_nonzero = self.features_nonzero,
                                                  act = tf.nn.relu,
                                                  dropout = self.dropout,
                                                  logging = self.logging)(self.inputs)

        self.hidden2_std = GraphConvolution(input_dim = FLAGS.hidden,
                                            output_dim = FLAGS.hidden,
                                            adj = self.adj,
                                            act = lambda x: x,
                                            dropout = self.dropout,
                                            logging = self.logging)(self.hidden1_std)

        self.z_mean = GraphConvolution(input_dim = FLAGS.hidden,
                                       output_dim = FLAGS.dimension,
                                       adj = self.adj,
                                       act = lambda x: x,
                                       dropout = self.dropout,
                                       logging = self.logging)(self.hidden2_mean)

        self.z_log_std = GraphConvolution(input_dim = FLAGS.hidden,
                                          output_dim = FLAGS.dimension,
                                          adj = self.adj,
                                          act = lambda x: x,
                                          dropout = self.dropout,
                                          logging = self.logging)(self.hidden2_std)

        self.z = self.z_mean + tf.random_normal([self.n_samples, FLAGS.dimension]) * tf.exp(self.z_log_std)

        self.reconstructions = InnerProductDecoder(fastgae = FLAGS.fastgae, # Whether to use FastGAE
                                                   sampled_nodes = self.sampled_nodes, # FastGAE subgraph
                                                   act = lambda x: x,
                                                   logging = self.logging)(self.z_mean)