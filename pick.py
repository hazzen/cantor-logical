import csv
import logging
import os
import random
import re
import sys

TWEETED_FILE = 'tweeted.txt'

PREFIXES = [
    'ein',
    'ver',
    'vor',
    'aus',
    'an',
]
PREFIXE_RE = re.compile(
  '|'.join('(?:%s)' % prefix for prefix in PREFIXES),
  re.IGNORECASE)

ALTERNATE_DEFS = {
    # Prefixes
    'ab-': [['from/off/down-']],
    'an-': [['up/on-']],
    'auf-': [['up-']],
    'aus-': [['out/off-']],
    'be-': [['touching/changing-']],
    'bei-': [['near/with-']],
    'da-': [['there-']],
    'durch-': [['through-']],
    'ein-': [['into-/one-']],
    'emp-': [['not-']],
    'ent-': [['begin/remove/reverse-']],
    'er-': [['ending-']],
    'ge-': [['past/multiple-']],
    'her-': [['towards-']],
    'hin-': [['away-']],
    'miss-': [['worse-']],
    'mit-': [['with/co-']],
    'nach-': [['after/again-']],
    'um-': [['round/re/over-']],
    'un-': [['absence of-']],
    'ur-': [['proto-']],
    'ver-': [['for/to-']],
    'vor-': [['before-']],
    'wieder-': [['re-']],
    'zer-': [['split/spoil-']],
    'zu-': [['to/by/on/open-']],
    'zusammen-': [['together-']],
    'zwie-': [['twice-']],

    # Suffixes
    '-al': [['-of']],
    '-bar': [['-able']],
    '-chen': [['-diminuitive']],
    '-ei': [['-y']],
    '-elchen': [['-diminuitive']],
    '-ell': [['-pertaining to']],
    '-er': [['-doer']],
    '-erlei': [['-kinds']],
    '-erweise': [['-ly']],
    '-esk': [['-esque']],
    '-end': [['-ing']],
    '-gen': [['-producer']],
    '-heit': [['-ness']],
    '-ig': [['-y']],
    '-keit': [['-ness']],
    '-kunde': [['-science']],
    '-kunst': [['-art/skill']],
    '-lein': [['-diminuitive']],
    '-ler': [['-doer']],
    '-lich': [['-able']],
    '-ling': [['-ling']],
    '-los': [['-less']],
    '-nis': [['-ness']],
    '-sam': [['-worthy']],
    '-sch': [['\'-s']],
    '-seits': [['-side']],
    '-sel': [['-ing']],
    '-ung': [['-ing']],
    '-unter': [['-under']],
    '-weise': [['-ly']],

    # Shit-list
    '-st': [],
    'es': [],
    'st': [],
    'zen': [],
    'bar': [],
    '-in': [],
    'abt': [],
    'unter': [],
    'met': [],
    'ren': [],

    # Special-cases
    'acht': [['eight/ban']],
}

SPLIT_RE = re.compile('[;,]')

WIKI_LINK_WITH_SPLIT = re.compile('\[\[[^|]*\|([^]]*)\]\]')
WIKI_LINK = re.compile('\[\[([^]|]*)\]\]')

class Picker(object):
  def __init__(self, english=None, german=None):
    self.english = english
    self.german = german
    self.blacklist = self.ReadBlacklist()

  def ReadBlacklist(self):
    blacklist = []
    for line in open(TWEETED_FILE):
      blacklist.append(line.strip())
    return blacklist

  def WriteBlacklist(self):
    with open('.%s' % TWEETED_FILE, 'w') as scratch:
      scratch.writelines('%s\n' % s for s in self.blacklist)

  def FindMeOne(self, budget=100):
    options = random.sample(
        [k for (k, v) in self.german.iteritems()
         if v.get('defs') and k not in self.blacklist],
        1000)
    for word in options:
      logging.info('Trying %s', word)
      had_one = False
      for possibility in self.PossibilitiesFor(word):
        had_one = True
        if possibility:
          word, _, _ = possibility
          real_word = self.german[word]['word']
          tweet = self.PossibilityToReadable(possibility)
          if real_word not in self.blacklist and len(tweet) < budget:
            self.blacklist.append(real_word)
            return tweet
          else:
            logging.info('..."%s" over budget!', tweet)

      if not had_one:
        logging.info('...not possible')


  def PossibilityToReadable(self, possibility):
    word, parts, meanings = possibility
    info = self.german[word]
    logging.info('%s --> %s', possibility, info)
    real_word = info['word']
    real_definition = info['defs'][0]

    part_definitions = [' '.join(x[0]) for x in meanings]
    definition = ' - '.join(part_definitions)
    definition = definition.replace('- - ', '- ')
    definition = definition.replace(' - -', ' -')
    return '%s (%s).\nGerman for %s. Because of course it is.' % (
        real_word,
        definition,
        real_definition)

  def PossibilitiesFor(self, word):
    logging.debug('%s, %s', word, self.german[word])

    for possible in BreakWord(self.german, word):
      if possible[-4:] == '+in+':
        continue
      if possible.count('+') < 3:
        continue
      possibles = possible[:-1].split('+')
      meanings = [self._IsUsablePart(p) for p in possibles]
      valid = all(meanings)
      logging.debug('Trying defs...')
      for meaning, p in zip(meanings, possibles):
        logging.debug('  %s --> %s', p, meaning)
      if valid:
        print '...HIT!\n======='
        print possible.split('+'), self.german[word]
        print '  %s' % possible
        print meanings
        print '======='
        yield word, possible, meanings

  def _IsUsablePart(self, word):
    split_re = re.compile('\W')

    meanings = []
    if word in ALTERNATE_DEFS:
      return ALTERNATE_DEFS[word]
    info = (self.german.get(word) or
            self.german.get(word + '-') or
            self.german.get('-' + word))
    if not info:
      return False
    for definition in info['defs']:
      meaning = []
      definition = definition.replace('Inseparable verbal prefix', '')
      definition = definition.replace('Separable verb prefix', '')
      for english_word in split_re.split(definition):
        if english_word and english_word.lower() not in self.english:
          logging.debug('Bad: %r', english_word)
          return False
        elif english_word:
          meaning.append(english_word)
      meanings.append(meaning)
    return meanings


def BreakWord(dictionary, word, in_word=0, indent=''):
  suffix_ok = in_word
  if in_word < 0:
    in_word = 0
  logging.debug('%s :: %s', indent, word)
  if not word:
    logging.debug('%sbottomed-out=%s', indent, in_word)
  if not word and in_word != 1:
    yield ''
  #elif len(word) < 3:
  #  yield 'XXX'
  hit_prefix = hit_suffix = False
  for end in xrange(2, 1 + len(word)):
    sub_word = word[:end]
    valid = sub_word in dictionary
    logging.debug('%s%s [%s]', indent, sub_word, in_word)
    if valid:
      logging.debug('%s...good', indent)
      for tail in BreakWord(dictionary, word[end:], in_word=in_word+1, indent='  ' + indent):
        yield '%s+%s' % (sub_word, tail)
    # Rule we don't have: if suffixing, there can be a vowel change
    # from unstressed to stressed.
    maybe_verb = (len(sub_word) > 2 and
                  dictionary.get(sub_word + 'en', {}).get('part', '') == 'Verb')
    suffix = '-%s' % sub_word in dictionary
    suffix_minus_one = '-%s' % sub_word[1:] in dictionary
    prefix = '%s-' % sub_word in dictionary
    prefix_minus_one = '%s-' % sub_word[:-1] in dictionary

    if maybe_verb:
      logging.debug('%s%s-en', indent, sub_word)
      for tail in BreakWord(dictionary, word[end:], in_word=in_word+1, indent='  ' + indent):
        yield '%sen+%s' % (sub_word, tail)

    if suffix_ok and (suffix or (suffix_minus_one and not hit_suffix)):
      logging.debug('%s-%s',  indent, sub_word)
      for tail in BreakWord(dictionary, word[end:], in_word=-1, indent='  ' + indent):
        hit_suffix = True
        yield '-%s+%s' % (sub_word, tail)

    if prefix or (prefix_minus_one and not hit_prefix):
      logging.debug('%s%s-', indent, sub_word)
      for tail in BreakWord(dictionary, word[end:], in_word=0, indent='  ' + indent):
        hit_prefix = True
        yield '%s-+%s' % (sub_word, tail)


BAD_CONTEXTS = [
    'organic',
    'compound',
]
BAD_CONTEXTS_RE = re.compile(
  '^.*{[^}]*(?:%s)[^}]*}' % (
    '|'.join('(?:%s)' % context for context in BAD_CONTEXTS)),
  re.IGNORECASE)

def HasScientificContext(definition):
  return BAD_CONTEXTS_RE.match(definition)

def RemoveAnnotation(definition):
  depth = 0
  initial = start = end = definition.find('{')
  if initial != -1:
    depth = 1
  loops = 0
  while depth or initial != -1:
    loops += 1
    next_start = definition.find('{', start + 1)
    next_end = definition.find('}', end + 1)
    if next_start != -1 and next_start < next_end:
      depth += 1
      start = next_start
    elif next_end != -1:
      depth -= 1
      end = next_end
      if not depth:
        old = definition
        definition = definition[:initial] + definition[next_end + 2:]
        initial = start = end = definition.find('{')
        if initial != -1:
          depth = 1
    else:
      # Bad data - no closing }, so trim the rest.
      definition = definition[:initial]
      depth = 0
      initial = -1

  parts = definition.split('{')
  tails = [part.split('}') for part in parts]
  if any(len(tail) > 2 for tail in tails):
    raise Exception('Bad tail: %r' % definition)
  definition = ''.join(tail[-1] for tail in tails)
  definition = definition.replace('e.g.,', '')
  definition = WIKI_LINK_WITH_SPLIT.sub(r'\1', definition)
  definition = WIKI_LINK.sub(r'\1', definition)
  return definition

GOOD_PARTS = set(['Adjective', 'Noun', 'Verb', 'Prefix', 'Suffix', 'Numeral'])


def ReadDict(path, only_with_links=False, only_words=False):
  data = {}
  with open(path, 'rb') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for language, word, part, definition in reader:
      debug = False
      if 'Low German' in language:
        continue
      if part not in GOOD_PARTS and not only_words:
        continue
      if only_words:
        data[word.lower()] = True
        continue
      if only_with_links and -1 == definition.find('[['):
        continue
      if HasScientificContext(definition):
        continue
      definition = RemoveAnnotation(definition)
      # TODO: deal with commas in parentheticals.
      definitions = SPLIT_RE.split(definition)
      defs = [d.strip('# ') for d in definitions if d.strip('# ')]
      if word.lower() in data:
        data[word.lower()]['defs'].extend(defs)
      else:
        data[word.lower()] = dict(part=part, word=word, defs=defs)

  return data

_PICKER = None

def WriteBlacklist():
  os.rename('.%s' % TWEETED_FILE, TWEETED_FILE)
  global _PICKER
  _PICKER.WriteBlacklist()

def GetMeATweet(force_words=None):
  global _PICKER
  if not _PICKER:
    german = ReadDict('data/german.tsv', only_with_links=False)
    english = ReadDict('data/english.tsv', only_words=True)
    _PICKER = Picker(german=german, english=english)

  if force_words:
    for word in force_words:
      logging.info('Doing %s', word)
      for possibility in _PICKER.PossibilitiesFor(word):
        logging.info('  %s', _PICKER.PossibilityToReadable(possibility))
  else:
    tweet = _PICKER.FindMeOne()
    _PICKER.WriteBlacklist()
    return tweet


def main(argv):
  trouble_words = argv[1:]

  log_level = logging.INFO
  if trouble_words:
    log_level = logging.DEBUG

  logging.basicConfig(
      level=log_level,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

  found = GetMeATweet(force_words=trouble_words)
  if found:
    print found

if __name__ == '__main__':
  main(sys.argv)
