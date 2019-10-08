import os
import shutil
import tempfile
import unittest

import numpy as np
import tensorflow as tf
from keras_preprocessing.text import Tokenizer

from headliner.losses import masked_crossentropy
from headliner.model.summarizer_simple import SummarizerSimple
from headliner.preprocessing.preprocessor import Preprocessor
from headliner.preprocessing.vectorizer import Vectorizer


class TestSummarizer(unittest.TestCase):

    def setUp(self) -> None:
        np.random.seed(42)
        tf.random.set_seed(42)
        self.temp_dir = tempfile.mkdtemp(prefix='TestSummarizerTmp')

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_serde_happy_path(self) -> None:
        preprocessor = Preprocessor()
        tokenizer = Tokenizer(oov_token='<unk>')
        tokenizer.fit_on_texts(['a b c {} {}'.format(
            preprocessor.start_token, preprocessor.end_token)])
        vectorizer = Vectorizer(tokenizer, tokenizer)
        summarizer = SummarizerSimple(lstm_size=10,
                                      max_prediction_len=10,
                                      embedding_decoder_trainable=False,
                                      embedding_size=10)
        summarizer.init_model(preprocessor=preprocessor,
                              vectorizer=vectorizer)

        # we need at least a train step to init the weights
        train_step = summarizer.new_train_step(masked_crossentropy, batch_size=1, apply_gradients=True)
        train_seq = tf.convert_to_tensor(np.array([[1, 1, 1]]), dtype=tf.int32)
        train_step(train_seq, train_seq)

        save_dir = os.path.join(self.temp_dir, 'summarizer_serde_happy_path')
        summarizer.save(save_dir)
        summarizer_loaded = SummarizerSimple.load(save_dir)
        self.assertEqual(10, summarizer_loaded.lstm_size)
        self.assertEqual(10, summarizer_loaded.max_prediction_len)
        self.assertIsNotNone(summarizer_loaded.preprocessor)
        self.assertIsNotNone(summarizer_loaded.vectorizer)
        self.assertIsNotNone(summarizer_loaded.encoder)
        self.assertIsNotNone(summarizer_loaded.decoder)
        self.assertTrue(summarizer_loaded.encoder.embedding.trainable)
        self.assertFalse(summarizer_loaded.decoder.embedding.trainable)
        self.assertIsNotNone(summarizer_loaded.optimizer)

        pred = summarizer.predict_vectors('a c', '')
        pred_loaded = summarizer_loaded.predict_vectors('a c', '')
        np.testing.assert_almost_equal(
            pred['logits'], pred_loaded['logits'], decimal=6)