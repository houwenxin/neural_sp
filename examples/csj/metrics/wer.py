#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Define evaluation method by Word Error Rate (CSJ corpus)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import re
from tqdm import tqdm

from utils.io.labels.word import Idx2word
from utils.evaluation.edit_distance import compute_wer, wer_align


def do_eval_wer(model, model_type, dataset, label_type, data_size, beam_width,
                max_decode_len, eval_batch_size=None,
                progressbar=False, is_pos=False):
    """Evaluate trained model by Character Error Rate.
    Args:
        model: the model to evaluate
        model_type (string): ctc or attention or hierarchical_ctc or
            hierarchical_attention or nested_attention
        dataset: An instance of a `Dataset' class
        label_type (string): word_freq1 or word_freq5 or word_freq10 or word_freq15
        data_size (string): fullset or subset
        beam_width: (int): the size of beam
        max_decode_len (int): the length of output sequences
            to stop prediction when EOS token have not been emitted.
            This is used for seq2seq models.
        eval_batch_size (int, optional): the batch size when evaluating the model
        progressbar (bool, optional): if True, visualize the progressbar
        is_pos (bool, optional):
    Returns:
        wer_mean (float): An average of WER
    """
    # Reset data counter
    dataset.reset()

    idx2word = Idx2word(
        vocab_file_path='../metrics/vocab_files/' +
        label_type + '_' + data_size + '.txt')

    wer_mean = 0
    if progressbar:
        pbar = tqdm(total=len(dataset))  # TODO: fix this
    while True:
        batch, is_new_epoch = dataset.next(batch_size=eval_batch_size)

        # Decode
        if model_type in ['ctc', 'attention']:
            inputs, labels, inputs_seq_len, labels_seq_len, _ = batch
            labels_hyp = model.decode(inputs, inputs_seq_len,
                                      beam_width=beam_width,
                                      max_decode_len=max_decode_len)

        elif model_type in ['hierarchical_ctc', 'hierarchical_attention', 'nested_attention']:
            if is_pos:
                inputs, _, labels, inputs_seq_len, _, labels_seq_len, _ = batch
            else:
                inputs, labels, _, inputs_seq_len, labels_seq_len, _,  _ = batch
            labels_hyp = model.decode(inputs, inputs_seq_len,
                                      beam_width=beam_width,
                                      max_decode_len=max_decode_len,
                                      is_sub_task=is_pos)

        for i_batch in range(len(inputs)):

            ##############################
            # Reference
            ##############################
            if dataset.is_test:
                str_ref = labels[i_batch][0]
                # NOTE: transcript is seperated by space('_')
            else:
                # Convert from list of index to string
                if model_type in ['ctc', 'hierarchical_ctc']:
                    str_ref = idx2word(
                        labels[i_batch][:labels_seq_len[i_batch]])
                elif model_type in ['attention', 'hierarchical_attention', 'nested_attention']:
                    str_ref = idx2word(
                        labels[i_batch][1:labels_seq_len[i_batch] - 1])
                    # NOTE: Exclude <SOS> and <EOS>

            ##############################
            # Hypothesis
            ##############################
            str_hyp = idx2word(labels_hyp[i_batch])
            if model_type in ['attention', 'hierarchical_attention', 'nested_attention']:
                str_hyp = str_hyp.split('>')[0]
                # NOTE: Trancate by the first <EOS>

                # Remove the last space
                if len(str_hyp) > 0 and str_hyp[-1] == '_':
                    str_hyp = str_hyp[:-1]

            # Remove noise labels
            str_ref = re.sub(r'[NZ]+', '', str_ref)
            str_hyp = re.sub(r'[NZ]+', '', str_hyp)

            # Compute WER
            wer_mean += compute_wer(ref=str_ref.split('_'),
                                    hyp=str_hyp.split('_'),
                                    normalize=True)
            # substitute, insert, delete = wer_align(
            #     ref=str_hyp.split('_'),
            #     hyp=str_ref.split('_'))
            # print('SUB: %d' % substitute)
            # print('INS: %d' % insert)
            # print('DEL: %d' % delete)

            if progressbar:
                pbar.update(len(inputs))

        if is_new_epoch:
            break

    if progressbar:
        pbar.close()

    # Reset data counters
    dataset.reset()

    wer_mean /= len(dataset)

    return wer_mean
