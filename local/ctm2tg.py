#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set fileencoding=utf-8
#
# ctm2tg: a script to convert CTM files from Kaldi aligner 
# to Praat's TextGrid format
#
# Grupo FalaBrasil (2021)
# Universidade Federal do Pará
#
# author: apr 2019
# cassio batista - https://cassota.gitlab.io
# updated on apr 2021

import sys
import os
import shutil

TG_NAMES = [
    'fonemeas', 'silabas-fonemas', 'palavras-grafemas',
    'frase-fonemas', 'frase-grafemas',
]

CTM_SIL_ID = '1' # TODO: keep an eye on sil id occurrences -- CB


def check_ctm(filetype, filename):
    if filetype != 'graphemes' and filetype != 'phoneids':
        print('error: filetype %s is not acceptable' % filetype)
        sys.exit(1)
    if not os.path.isfile(filename):
        print('error: input file "%s" does not exist' % filename)
        sys.exit(1)
    elif not filename.endswith('%s.ctm' % filetype):
        print('error: input file "%s" does not have "%s.ctm" extension' % (filename, filetype))
        sys.exit(1)
    # https://stackoverflow.com/questions/2507808/how-to-check-whether-a-file-is-empty-or-not
    elif not os.stat(filename).st_size:
        print('error: input file "%s" appears to be empty' % filename)
        sys.exit(1)


def get_file_numlines(fp):
    for linenumber, content in enumerate(fp):
        pass
    fp.seek(0)
    return linenumber + 1


class TextGrid:
    def __init__(self):
        super(TextGrid, self).__init__()

    def check_outputdir(self, dirname):
        if os.path.isdir(dirname):
            if len(os.listdir(dirname)):
                ans = input('warning: dir "%s" is not empty. overwrite? [y/N] ' % dirname)
                if ans == 'y':
                    shutil.rmtree(dirname)
                    os.mkdir(dirname)
                else:
                    print('aborted.')
                    sys.exit(1)
        else:
            print('info: textgrid files will be stored under "%s" dir' % dirname)
            os.mkdir(dirname)

    def get_mainheader(self, xmax):
        return u'File type = "ooTextFile"'              + '\n' + \
            u'Object class = "TextGrid"'                + '\n' + \
            u'xmin = 0.00'                              + '\n' + \
            u'xmax = %.2f'                  % xmax      + '\n' + \
            u'tiers? <exists>'                          + '\n' + \
            u'size = 5'                                 + '\n' + \
            u'item []:'                                 + '\n'

    def get_itemheader(self, itm_id, name, xmax, intv_size):
        return u'\titem[%d]:'               % itm_id    + '\n' + \
            u'\t\tclass = "IntervalTier"'               + '\n' + \
            u'\t\tname  = "%s"'             % name      + '\n' + \
            u'\t\txmin  = 0.00'                         + '\n' + \
            u'\t\txmax  = %.2f'             % xmax      + '\n' + \
            u'\t\tintervals: size = %d'     % intv_size + '\n'

    def get_intervalcontent(self, intv_id, begin, end, token):
        return u'\t\tintervals[%d]'         % intv_id   + '\n' + \
            u'\t\t\txmin = %.2f'            % begin     + '\n' + \
            u'\t\t\txmax = %.2f'            % end       + '\n' + \
            u'\t\t\ttext = "%s"'            % token     + '\n' 

    def get_intervalsize(self, itm_id, tokenlist):
        if itm_id == 0:
            return len(tokenlist['phnid'])
        elif itm_id == 1:
            return len(tokenlist['sylph']) + tokenlist['phnid'].count(CTM_SIL_ID) 
        elif itm_id == 2:
            return len(tokenlist['graph']) - \
                       tokenlist['graph'].count('sil') + \
                       tokenlist['phnid'].count(CTM_SIL_ID)
        else:
            return 1

    def get_itemcontent(self, itm_id, tokenlist, start, finish):
        interval_size = self.get_intervalsize(itm_id, tokenlist)
        item_header = self.get_itemheader(itm_id+1,
                    TG_NAMES[item], finish['graph'][-1], interval_size)
        item_content     = ''
        interval_content = ''
        i = 0
        if item == 0: # fonemas
            p = 0
            while i < interval_size:
                if tokenlist['phnid'][i] == CTM_SIL_ID:
                    token = 'sil'
                else:
                    token = tokenlist['phone'][p]
                    p += 1
                interval_content += self.get_intervalcontent(i+1,
                            start['phnid'][i], finish['phnid'][i], token)
                i += 1
        elif item == 1: # silabas fonemas TODO
            interval_content = ''
            b = 0
            e = 0
            while len(tokenlist['phnid']):
                phoneid = tokenlist['phnid'].pop(0)
                if phoneid == CTM_SIL_ID:
                    token = 'sil'
                else:
                    token = tokenlist['sylph'].pop(0)
                    phone = tokenlist['phone'].pop(0)
                    while phone != token:
                        phone += tokenlist['phone'].pop(0)
                        tokenlist['phnid'].pop(0) # FIXME
                        e += 1
                interval_content += self.get_intervalcontent(i+1,
                            start['phnid'][b], finish['phnid'][e], token)
                i += 1
                b = e + 1
                e += 1
        elif item == 2: # palavras grafemas
            while i < interval_size:
                token = tokenlist['graph'][i]
                interval_content += self.get_intervalcontent(i+1,
                            start['graph'][i], finish['graph'][i], token)
                i += 1
        elif item == 3: # frase fonemas
            token = ' '.join(phonesyl for phonesyl in tokenlist['phrph'])
            interval_content = self.get_intervalcontent(i+1,
                        start['phnid'][0], finish['phnid'][-1], token)
        elif item == 4: # frase grafemas
            token = ' '.join(word for word in tokenlist['phrgr'])
            interval_content = self.get_intervalcontent(i+1,
                        start['graph'][0], finish['graph'][-1], token)
        else:
            print('wait a minute... there is something really wrong here.')
        return item_header + interval_content

if __name__=='__main__':
    if len(sys.argv) != 6:
        print('usage: %s <ctm-graph-file> <ctm-phoneid-file> '
              '<lex-dict> <syll-dict> <out-dir>' % sys.argv[0])
        print('  <ctm-graph-file> is the CTM file with graphemes')
        print('  <ctm-phoneid-file> is te CTM file with phonetic ids')
        print('  <lex-dict> is the lexicon (phonetic dictionary)')
        print('  <syll-dict> is the syllabic dictionary')
        print('  <out-dir> is the output dir to store the textgrid file')
        sys.exit(1)

    tg = TextGrid()

    ctm_graph_filename = sys.argv[1]
    ctm_phone_filename = sys.argv[2]
    lex_filename = sys.argv[3]
    syll_filename = sys.argv[4]
    tg_output_dirname = sys.argv[5]

    # sanity check 
    check_ctm('phoneids', ctm_phone_filename)
    check_ctm('graphemes', ctm_graph_filename)
    tg.check_outputdir(tg_output_dirname)

    ctm = {
        'graph':open(ctm_graph_filename, 'r'),
        'phnid':open(ctm_phone_filename, 'r')
    }

    ctm_lines = {
        'graph':get_file_numlines(ctm['graph']),
        'phnid':get_file_numlines(ctm['phnid'])
    }

    lex = {}
    with open(lex_filename) as f:
        for line in f:
            try:
                grapheme, phonemes = line.split('\t')
                lex[grapheme.strip()] = phonemes.strip()
            except ValueError:
                print('**lex problem: %s' % line, '\t' in line)
                lex[line.strip()] = line.strip()

    syll = {}
    with open(syll_filename) as f:
        for line in f:
            try:
                grapheme, syllables = line.split('\t')
                syll[grapheme.strip()] = syllables.strip()
            except ValueError:
                print('**syll problem: %s' % line)
                syll[line.strip()] = line.strip()

    fp_index = { 'graph': 0,  'phnid': 0  }
    start    = { 'graph': [], 'phnid': [], 'sylph': [] }
    finish   = { 'graph': [], 'phnid': [], 'sylph': [] }
    bt       = { 'graph': 0,  'phnid': 0  }
    dur      = { 'graph': 0,  'phnid': 0  }

    tokenlist = {
        'phnid':[], # 0 (1) phoneme ids as they appear in the CTM file
        'sylph':[], # 1 (2) phonemes separated by syllabification of graphemes
        'graph':[], # 2 (3) graphemes (words)
        'phrph':[], # 4 (5) phrase of phonemes separated by the space between graphemes
        'phrgr':[], # 3 (4) phrase of graphemes (words) 
        'phone':[], #       phonemes as they occur in the list of words
    }

    # treat .grapheme file
    filepath, chn, bt['graph'], dur['graph'], grapheme = ctm['graph'].readline().split()
    old_name = curr_name = filepath.split(sep='_', maxsplit=1).pop()
    start['graph'].append(float(bt['graph']))
    finish['graph'].append(float(bt['graph']) + float(dur['graph']))
    tokenlist['graph'].append(grapheme)
    fp_index['graph'] += 1
    while fp_index['phnid'] < ctm_lines['phnid']:
        while curr_name == old_name:
            if fp_index['graph'] >= ctm_lines['graph']:
                break
            filepath, chn, bt['graph'], dur['graph'], grapheme = ctm['graph'].readline().split()
            curr_name = filepath.split(sep='_', maxsplit=1).pop()
            start['graph'].append(float(bt['graph']))
            finish['graph'].append(float(bt['graph']) + float(dur['graph']))
            tokenlist['graph'].append(grapheme)
            fp_index['graph'] += 1

        # FIXME: dumb way to avoid the first word of the next sentence to be
        # appended to the end of the current one
        if fp_index['graph'] < ctm_lines['graph']:
            start['graph'].pop()
            finish['graph'].pop()
            tokenlist['graph'].pop()

        # treat .phoneids file
        filepath, chn, bt['phnid'], dur['phnid'], phoneme = ctm['phnid'].readline().split()
        curr_name = filepath.split(sep='_', maxsplit=1).pop()
        start['phnid'].append(float(bt['phnid']))
        finish['phnid'].append(float(bt['phnid']) + float(dur['phnid']))
        tokenlist['phnid'].append(phoneme)
        fp_index['phnid'] += 1
        while curr_name == old_name:
            if fp_index['phnid'] >= ctm_lines['phnid']:
                break
            filepath, chn, bt['phnid'], dur['phnid'], phoneme = ctm['phnid'].readline().split()
            curr_name = filepath.split(sep='_', maxsplit=1).pop()
            start['phnid'].append(float(bt['phnid']))
            finish['phnid'].append(float(bt['phnid']) + float(dur['phnid']))
            tokenlist['phnid'].append(phoneme)
            fp_index['phnid'] += 1

        # FIXME: dumb way to avoid the first phoneme of the next sentence to be
        # appended to the end of the current one
        if fp_index['phnid'] < ctm_lines['phnid']:
            start['phnid'].pop()
            finish['phnid'].pop()
            tokenlist['phnid'].pop()

        # prepare tg item's basic data structures
        tokenlist['phone'] = []
        for word in tokenlist['graph']:
            if word == '<UNK>':
                tokenlist['sylph'].append(word)
                tokenlist['phone'].append(word)
                tokenlist['phrph'].append(word)
                tokenlist['phrgr'].append(word)
                continue
            elif word == 'cinquenta':
                tokenlist['sylph'].append('si~')
                tokenlist['sylph'].append('kwe~')
                tokenlist['sylph'].append('ta')
            elif word == 'veloz':
                tokenlist['sylph'].append('ve')
                tokenlist['sylph'].append('lOjs')
            elif word == 'dez':
                tokenlist['sylph'].append('dEjs')
            else:
                for sylph in syll[word].split('-'):
                    tokenlist['sylph'].append(sylph.replace('\'',''))
            phonemes = lex[word]
            for phone in phonemes.split():
                tokenlist['phone'].append(phone)
            tokenlist['phrph'].append(phonemes.replace(' ', ''))
            tokenlist['phrgr'].append(word)

        # write things to textgrid file
        with open('%s/%s.TextGrid' % (tg_output_dirname, old_name), 'w') as f:
            sys.stdout.write('\r%s' % old_name)
            sys.stdout.flush()
            f.write(tg.get_mainheader(finish['graph'][-1]))
            for item in range(5):
                f.write(tg.get_itemcontent(item, tokenlist, start, finish))

        # flush vars
        start['graph']     = [float(bt['graph'])]
        finish['graph']    = [float(bt['graph']) + float(dur['graph'])]
        tokenlist['graph'] = [grapheme]
        old_name           = curr_name
        start['phnid']     = [float(bt['phnid'])]
        finish['phnid']    = [float(bt['phnid']) + float(dur['phnid'])]
        tokenlist['phnid'] = [phoneme]

        tokenlist['sylph'] = []
        tokenlist['phrph'] = []
        tokenlist['phrgr'] = []

    print('\tdone!')
    ctm['graph'].close()
    ctm['phnid'].close()
### EOF ###
