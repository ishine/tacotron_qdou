import os
from lib import sigproc as sp
from hparams import hparams_debug_string
from tacotron.alignment_synthesizer import AlignmentSynthesizer
from tacotron.synthesizer import Synthesizer
from tacotron.pml_synthesizer import Configuration, PMLSynthesizer
from infolog import log
from tqdm import tqdm
import numpy as np
from datasets import pml_dir, wav_dir, mel_dir
import warnings

from tacotron.utils import plot

import sys
sys.path.append('/home/dawna/tts/qd212/lib_QDOU/')
from IO_wav_lab import get_file_list

################# strict synthesis
def run_eval(args, checkpoint_path, output_dir, hparams, sentences, flag_to_wav=False, checkpoint_eal=None, 
             flag_check=False, cmu_dict=None):
#     import pdb
#     pdb.set_trace()
#     sentences = sentences[:3]
    log(hparams_debug_string())

    # use the correct synthesizer for the model type
    if args.variant not in ['tacotron_orig', 'tacotron_bk2orig']:
        cfg = Configuration(hparams.sample_rate, hparams.pml_dimension)
        synth = PMLSynthesizer(cfg)
    else:
        synth = Synthesizer()
    synth.load(checkpoint_path, hparams, model_name=args.variant, checkpoint_eal=checkpoint_eal, flag_online=args.online)
    
    if hparams.use_cmudict: sentences = sentences_2_phones(sentences, cmu_dict)
#     import pdb; pdb.set_trace()
#     with open('/home/dawna/tts/qd212/models/tacotron/tests/sentences_asup.txt','w') as f:
#         f.write("\n".join(sentences))
#     pdb.set_trace()
    
    if flag_check:
        _eval_check(synth, args, checkpoint_path, output_dir, hparams, sentences, flag_to_wav, checkpoint_eal)
    else:
        _eval_tgt(synth, args, checkpoint_path, output_dir, hparams, sentences, flag_to_wav, checkpoint_eal)
    return

def _eval_check(synth, args, checkpoint_path, output_dir, hparams, sentences, flag_to_wav, checkpoint_eal):
    synth_dir = os.path.join(output_dir, 'eval','alignment_check/npy')
    os.makedirs(synth_dir, exist_ok=True)
    
    tmp_alignment = synth.synthesize_check(sentences)
    name_list = get_file_list('/home/dawna/tts/qd212/data/lj/merlinData/file_id_list.scp')[13050:13050+50]
    for j, a in enumerate(tmp_alignment):
        if j<50: path = os.path.join(synth_dir, '%s.npy' % name_list[j])
        else: path = os.path.join(synth_dir, 'eval-%d.npy' % j)
        print('Writing {}...'.format(path))
        np.save(path, a)

def _eval_tgt(synth, args, checkpoint_path, output_dir, hparams, sentences, flag_to_wav, checkpoint_eal):
    synth_dir = os.path.join(output_dir, 'eval','wav') if flag_to_wav else os.path.join(output_dir, 'eval','npy')
    os.makedirs(synth_dir, exist_ok=True)
    
    # Set up denormalisation parameters for synthesis
    mean_path = os.path.abspath(os.path.join(args.base_dir, args.training_dir, 'pml_data/mean.dat'))
    std_path = os.path.abspath(os.path.join(args.base_dir, args.training_dir, 'pml_data/std.dat'))
    mean_norm = None
    std_norm = None

    if os.path.isfile(mean_path) and os.path.isfile(std_path):
        mean_norm = np.fromfile(mean_path, 'float32')
        std_norm = np.fromfile(std_path, 'float32')
    else:
        warnings.warn('No mean or standard deviation files found at locations {} and {}'.format(mean_path, std_path))

    print('Synthesizing to {}...'.format(synth_dir))
    if flag_to_wav:
        wavs = synth.synthesize(sentences, to_wav=True, mean_norm=mean_norm, std_norm=std_norm,
                                spec_type=hparams.spec_type)
        for i, wav in enumerate(wavs):
            path = os.path.join(synth_dir, 'eval-%d.wav' % i)
            print('Writing {}...'.format(path))
            if args.variant not in ['tacotron_orig', 'tacotron_bk2orig']:
                sp.wavwrite(path, wav, hparams.sample_rate, norm_max_ifneeded=True, verbose=0)
            else:
                with open(path, 'wb') as f:
                    f.write(wav)
    
    else:
        import pdb; pdb.set_trace()
        tgt_features_matrix = synth.synthesize(sentences, to_wav=False, mean_norm=mean_norm, std_norm=std_norm,
                                spec_type=hparams.spec_type)
        name_list = get_file_list('/home/dawna/tts/qd212/data/lj/merlinData/file_id_list.scp')[13050:13050+50]
        for i, f in enumerate(tgt_features_matrix):
            if i<50: path = os.path.join(synth_dir, '%s.npy' % name_list[i])
            else: path = os.path.join(synth_dir, 'eval-%d.npy' % i)
            print('Writing {}...'.format(path))
            np.save(path, f, allow_pickle=False)
#################


################# gta / eal synthesis
def run_synthesis(args, checkpoint_path, output_dir, hparams, flag_connect_NV=False, checkpoint_eal=None, flag_check=False, cmu_dict=None):
    gta = (args.gta == 'True')
    eal = (args.eal == 'True')

    if eal:
        synth_dir = 'eal'
        gta = False # disable ground truth alignment mode if explicit alignment locking is enabled
        if checkpoint_eal is None: checkpoint_eal = checkpoint_path
    elif gta:
        synth_dir = 'gta'
    else:
        synth_dir = 'natural'

    if flag_check:
        synth_dir = os.path.join(output_dir, synth_dir, 'alignment_check/npy')
    else:
        synth_dir = os.path.join(output_dir, synth_dir, 'npy')

    # create the output path if it does not exist
    os.makedirs(synth_dir, exist_ok=True)

    metadata_filename = os.path.join(args.base_dir, args.training_dir, '{}.txt'.format(args.dataset))
    log(hparams_debug_string())
    
    if args.variant not in ['tacotron_orig', 'tacotron_bk2orig']:
        cfg = Configuration(hparams.sample_rate, hparams.pml_dimension)
        synth = PMLSynthesizer(cfg)
    else:
        synth = Synthesizer()

    with open(metadata_filename, encoding='utf-8') as f:
        metadata = [line.strip().split('|') for line in f]
        hours = sum((int(x[2]) for x in metadata)) * hparams.frame_shift_ms / (3600 * 1000)
        log('Loaded metadata for %d examples (%.2f hours)' % (len(metadata), hours))

    if eal:
        align_synth = AlignmentSynthesizer()
        align_synth.load(checkpoint_path, hparams, cut_lengths=False, gta=True, model_name=args.variant)

    log('Starting synthesis')
    pml_path = os.path.join(args.base_dir, args.training_dir, pml_dir)
    wav_path = os.path.join(args.base_dir, args.training_dir, wav_dir)
    mel_path = os.path.join(args.base_dir, args.training_dir, mel_dir)

#     import pdb
#     pdb.set_trace()
    
    for i in tqdm(range(0, len(metadata), args.batch_size)):
        texts = []
        pml_filenames = []
        wav_filenames = []
        mel_filenames = []
        tgt_filenames_NV = []

        for meta in metadata[i:min(i + args.batch_size, len(metadata))]:
            texts.append(meta[5])
            pml_filenames.append(os.path.join(pml_path, meta[3]))
            wav_filenames.append(os.path.join(wav_path, meta[6]))
            mel_filenames.append(os.path.join(mel_path, meta[1]))
            tgt_filenames_NV.append(os.path.join(synth_dir, meta[6].replace('.wav','.npy')))

        basenames = [os.path.basename(p).replace('.npy', '').replace('pml-', '') for p in pml_filenames]
        tgt_filenames = mel_filenames if args.variant in ['tacotron_orig', 'tacotron_bk2orig'] else pml_filenames
        
        if hparams.use_cmudict: texts = sentences_2_phones(texts, cmu_dict)

#         print(i)
#         pdb.set_trace()

        if eal:
            if args.online:
                locked_alignments = None
                log('locked_alignments will be computed online')
            else:
                locked_alignments = align_synth.synthesize(texts, tgt_filenames=tgt_filenames)
                log('Alignments synthesized with shape: {}'.format(locked_alignments.shape))
            synth.load(checkpoint_eal, hparams, eal=True, model_name=args.variant,
                   logs_enabled=False, locked_alignments=locked_alignments, flag_online=args.online)
        else:
            log('locked_alignments is None')
            synth.load(checkpoint_path, hparams, gta=True, model_name=args.variant,
                       logs_enabled=False, locked_alignments=None)

        if flag_check:
            _synthesis_check(args, checkpoint_path, output_dir, hparams, flag_connect_NV, checkpoint_eal, 
                             texts, tgt_filenames, tgt_filenames_NV, basenames, synth_dir, synth)
        else:
            _synthesis_tgt(args, checkpoint_path, output_dir, hparams, flag_connect_NV, checkpoint_eal, 
                           texts, tgt_filenames, tgt_filenames_NV, basenames, synth_dir, synth)

    log('Synthesized tgt / alignment at {}'.format(synth_dir))
    return

def _synthesis_check(args, checkpoint_path, output_dir, hparams, flag_connect_NV, checkpoint_eal, 
                     texts, tgt_filenames, tgt_filenames_NV, basenames, synth_dir, synth):
    tmp_alignment = synth.synthesize_check(texts, tgt_filenames)
    for j, a in enumerate(tmp_alignment):
        np.save(tgt_filenames_NV[j], a)

def _synthesis_tgt(args, checkpoint_path, output_dir, hparams, flag_connect_NV, checkpoint_eal, 
                   texts, tgt_filenames, tgt_filenames_NV, basenames, synth_dir, synth):
    tgt_features = synth.synthesize(texts, tgt_filenames)
    for j, basename in enumerate(basenames):
        if args.variant in ['tacotron_bk2orig']: tmp_filename = os.path.join(synth_dir, 'spec-{}.npy'.format(basename))
        else: tmp_filename = os.path.join(synth_dir, 'pml-{}.npy'.format(basename))

        if flag_connect_NV: np.save(tgt_filenames_NV[j], tgt_features[j], allow_pickle=False)
        else: np.save(tmp_filename, tgt_features[j], allow_pickle=False)
    
#################

    
#################
def save_alignment(args, checkpoint_path, output_dir, hparams, cmu_dict=None):
    synth_dir = os.path.join(output_dir, 'gta', 'alignment/npy') # qd212
    os.makedirs(synth_dir, exist_ok=True)

    metadata_filename = os.path.join(args.base_dir, args.training_dir, '{}.txt'.format(args.dataset))
    log(hparams_debug_string())

    with open(metadata_filename, encoding='utf-8') as f:
        metadata = [line.strip().split('|') for line in f]
        hours = sum((int(x[2]) for x in metadata)) * hparams.frame_shift_ms / (3600 * 1000)
        log('Loaded metadata for %d examples (%.2f hours)' % (len(metadata), hours))

    align_synth = AlignmentSynthesizer()
    align_synth.load(checkpoint_path, hparams, cut_lengths=False, gta=True, model_name=args.variant)

    log('Starting synthesis')
    pml_path = os.path.join(args.base_dir, args.training_dir, pml_dir)
    wav_path = os.path.join(args.base_dir, args.training_dir, wav_dir)
    mel_path = os.path.join(args.base_dir, args.training_dir, mel_dir)

#     import pdb
#     pdb.set_trace()
    
    for i in tqdm(range(0, len(metadata), args.batch_size)):
        texts = []
        pml_filenames = []
        wav_filenames = []
        alignment_filenames = []
        mel_filenames = []

        for meta in metadata[i:min(i + args.batch_size, len(metadata))]:
            texts.append(meta[5])
            pml_filenames.append(os.path.join(pml_path, meta[3]))
            wav_filenames.append(os.path.join(wav_path, meta[6]))
            alignment_filenames.append(os.path.join(synth_dir, meta[6].replace('.wav','_align.npy')))
            mel_filenames.append(os.path.join(mel_path, meta[1]))
            
        if hparams.use_cmudict: texts = sentences_2_phones(texts, cmu_dict)
        
        tgt_filenames = mel_filenames if args.variant in ['tacotron_bk2orig'] else pml_filenames
        locked_alignments = align_synth.synthesize(texts, tgt_filenames=tgt_filenames)
        log('Alignments synthesized with shape: {}'.format(locked_alignments.shape))
        
#         print(i)
#         pdb.set_trace()

        for j, a in enumerate(alignment_filenames):
            np.save(a, locked_alignments[j], allow_pickle=False)
    return
#################

#################
def _get_cmu_dict(datadir):
    from tacotron.utils import cmudict
    cmudict_path = os.path.join(datadir, 'cmudict-0.7b')
    if not os.path.isfile(cmudict_path):
        raise Exception('If use_cmudict=True, you must download ' +
                        'http://svn.code.sf.net/p/cmusphinx/code/trunk/cmudict/cmudict-0.7b to %s' % cmudict_path)
    cmu_dict = cmudict.CMUDict(cmudict_path, keep_ambiguous=False)
    log('Loaded CMUDict with %d unambiguous entries' % len(cmu_dict))
    return cmu_dict

def _do_get_arpabet(word, cmu_dict):
    arpabet = cmu_dict.lookup(word)
    return '{%s}' % arpabet[0] if arpabet is not None else word

def sentences_2_phones(sentences, cmu_dict):
#     cmu_dict = _get_cmu_dict(datadir)
    phones = [' '.join([_do_get_arpabet(word, cmu_dict) for word in text.split(' ')]) for text in sentences]
    return phones


# import re
# def sentences_2_phones(sentences, cmu_dict):
# #     cmu_dict = _get_cmu_dict(datadir)
#     phones = [' '.join([_do_get_arpabet(word, cmu_dict) for word in text.split(' ')]) for text in sentences]
    
#     rep_list = [['H',''], ['HH',''], ['AH','OH'], ['AA','OH'], ['IY','UW'], ['TH','S'], ['TH','Z'], ['DH','S'], ['DH','Z'], ['DH','D'], ['IH','IY'], ['AA','AE'], ['OW','OH'], ['EY','EH'], ['JH','ZH'], ['CH','SH'], ['Y','JH']]
#     rep = {r[0]:r[1] for r in rep_list}
#     # use these three lines to do the replacement
#     rep = dict((re.escape(k), v) for k, v in rep.items()) 
#     #Python 3 renamed dict.iteritems to dict.items so use rep.items() for latest versions
#     pattern = re.compile("|".join(rep.keys()))
#     phones = pattern.sub(lambda m: rep[re.escape(m.group(0))], phones)
    
#     return phones
#################


#################
def tacotron_synthesize(args, hparams, checkpoint, sentences=None, checkpoint_eal=None):
#     output_dir = 'tacotron_' + args.output_dir
    output_dir = args.output_dir
    
#     import pdb
#     pdb.set_trace()
    cmu_dict = _get_cmu_dict(os.path.join(args.base_dir,args.training_dir)) if hparams.use_cmudict else None
    
    flag_check = False # True False
    
    if args.mode == 'synthesis':
        run_synthesis(args, checkpoint, output_dir, hparams, flag_connect_NV=True, checkpoint_eal=checkpoint_eal, flag_check=flag_check, 
                      cmu_dict=cmu_dict)
    elif args.mode == 'eval':
        run_eval(args, checkpoint, output_dir, hparams, sentences, checkpoint_eal=checkpoint_eal, flag_check=flag_check, 
                 cmu_dict=cmu_dict)
    elif args.mode == 'alignment':
        save_alignment(args, checkpoint, output_dir, hparams, cmu_dict=cmu_dict)
#################