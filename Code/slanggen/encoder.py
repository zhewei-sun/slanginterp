import io
import abc
import pickle

import numpy as np

from .util import *

from sentence_transformers import SentenceTransformer

class WordEncoder:
    
    @abc.abstractmethod
    def __init__(self):
        raise NotImplementedError()
    
    @abc.abstractmethod
    def embed_word(self, word):
        raise NotImplementedError()
        
    def norm_embed(self, word):
        vec = self.embed_word(word)
        return vec / np.linalg.norm(vec)
    
class FTEncoder(WordEncoder):
    
    def __init__(self, embed_file_name, do_cache=False):

        word = np.load(embed_file_name+'_word.npy')
        embed = np.load(embed_file_name+'_embed.npy')
        
        self.embeddings = {}
        
        for i in range(word.shape[0]):
            self.embeddings[word[i]] = embed[i]
        
        self.vocab = set(word)
        self.E = embed.shape[1]
        
        self.do_cache = do_cache
        if self.do_cache:
            self.cache = set()
    
    def embed_word(self, word):
        if self.do_cache:
            self.cache.add(word)
        return self.embeddings[word]
    
    def cache_embed(self, path):
        if not self.do_cache:
            return
        output = {}
        for word in self.cache:
            output[word] = self.embeddings[word]
        pickle.dump(output, open(path, 'wb'))
        
    def clear_cache(self):
        if not self.do_cache:
            return
        self.cache = set()
        
class FTCachedEncoder(WordEncoder):
    
    def __init__(self, embed_file_name):
        self.embeddings = pickle.load(open(embed_file_name, 'rb'))
        
        self.vocab = set(self.embeddings.keys())
        self.E = self.embeddings[list(self.embeddings.keys())[0]].shape[0]
        
    def embed_word(self, word):
        return self.embeddings[word]

class SenseEncoder:
    
    @abc.abstractmethod
    def __init__(self):
        raise NotImplementedError()
    
    def encode_dataset(self, dataset, slang_ind, encode_test=True):
        
        embeds = {}
        
        def collect_slang_sents(dataset, ind):
            sentences = []
            for i in ind:
                sentences.append(' '.join(simple_preprocess(dataset.slang_data[i].def_sent)))
            return sentences
        
        embeds['train'] = self.encode_sentences(collect_slang_sents(dataset, slang_ind.train))
        embeds['dev'] = self.encode_sentences(collect_slang_sents(dataset, slang_ind.dev))
        if encode_test:
            embeds['test'] = self.encode_sentences(collect_slang_sents(dataset, slang_ind.test))

        sentences = []
        for i in range(len(dataset.vocab)):
            word = dataset.vocab[i]
            for d in dataset.conv_data[word].definitions:
                sentences.append(' '.join(simple_preprocess(d['def'])))
          
        embeds['standard'] = self.encode_sentences(sentences)
        
        return embeds
    
    @abc.abstractmethod
    def encode_sentences(self, sentences):
        raise NotImplementedError()
        
class SBertEncoder(SenseEncoder):
    
    def __init__(self, sbert_model_name=None, name=None):
        
        if sbert_model_name is None:
            sbert_model_name = 'bert-base-nli-mean-tokens'
            self.name = 'sbert_base'
        elif name is not None:
            self.name = name
        else:
            self.name = sbert_model_name
            
        self.sbert_model = SentenceTransformer(sbert_model_name)
        
    def encode_sentences(self, sentences):
        
        sbert_embeddings = np.asarray(self.sbert_model.encode(sentences))
        return normalize_L2(sbert_embeddings, axis=1)