# -*- coding: utf-8 -*-
import sys
import os
import subprocess # to call the command for stanford corenlp tokenizer
import collections # to count vocab_counter
import struct
import tensorflow as tf # to serialize data
from tensorflow.core.example import example_pb2 # to serialize data

# instances that should be adjusted by host
num_of_data_pair = 0
VOCAB_SIZE = 50000
CHUNK_SIZE = 1000 # num examples per chunk, for the chunked data

dm_single_close_quote = u'\u2019' # unicode
dm_double_close_quote = u'\u201d'
END_TOKENS = ['.', '!', '?', '...', "'", "`", '"', dm_single_close_quote, dm_double_close_quote, ")"] # acceptable ways to end a sentence

# Get to the point code use these to separate the summary sentences in the .bin datafiles
SENTENCE_START = '<s>'
SENTENCE_END = '</s>'

content_tokenized_dir = "content_tokenized"
headline_tokenized_dir = "headline_tokenized"
finished_files_dir = "finished_files" # directory that contains bin files
chunks_dir = os.path.join(finished_files_dir, "chunked")


def set_num_of_data_pair(dir):
    global num_of_data_pair
    num_of_data_pair = len(os.listdir(dir))


def check_num_data(data_dir, num_expected):
    num_data = len(os.listdir(data_dir))
    if num_data != num_expected:
        raise Exception("data directory %s contains %i data but should contain %i data" % (data_dir, num_expected, num_data))


def tokenize_data(raw_text_dir, tokenized_text_dir):
    """Maps a whole directory of .text files to a tokenize version using Stanfrod CoreNLP Tokenizer"""
    print("Preparing to tokenize %s to %s..." % (raw_text_dir, tokenized_text_dir))
    texts = os.listdir(raw_text_dir)
    # make IO list file
    print("Making list of files to tokenize...")
    with open("mapping.txt", "w") as f:
        for s in texts:
            f.write("%s \t %s\n" % (os.path.join(raw_text_dir, s), os.path.join(tokenized_text_dir, s)))
    command = ['java', 'edu.stanford.nlp.process.PTBTokenizer', '-ioFileList', '-preserveLines', 'mapping.txt']
    print("Tokenizing %i files in %s and saving in %s..." % (len(texts), raw_text_dir, tokenized_text_dir))
    subprocess.call(command)
    print("Stanford CoreNLP Tokenizer has finished.")
    os.remove("mapping.txt")

    # Check that the tokenized data directory contains the same number of files as the original directory
    num_original = len(os.listdir(raw_text_dir))
    num_tokenized = len(os.listdir(tokenized_text_dir))
    if num_original != num_tokenized:
        raise Exception("The tokenized data directory %s contains %i files, but it should contain the same number as %s (which has %i files). Was there an error during tokeniziation?" % (tokenized_text_dir, num_tokenized, raw_text_dir, num_original))
    print("Successfully finished tokeinzing %s to %s.\n" % (raw_text_dir, tokenized_text_dir))


def read_text_file(text_file):
  lines = []
  with open(text_file, "rb") as f:
    for line in f:
      line = line.decode('utf-8')
      lines.append(line.strip())
  return lines    


def fix_missing_period(line):
  """Adds a period to a line that is missing a period"""
  if "@highlight" in line: return line
  if line=="": return line
  if line[-1] in END_TOKENS: return line # if there is no end token at the end of the sentence
  return line + " ."


def get_art_abs(story_file):
  lines = read_text_file(story_file)
  # Lowercase everything
  lines = [line.lower() for line in lines]
  # Put periods on the ends of lines that are missing them (this is a problem in the dataset because many image captions don't end in periods; consequently they end up in the body of the article as run-on sentences)
  lines = [fix_missing_period(line) for line in lines]
  # Separate out article and abstract sentences
  article_lines = []
  highlights = []
  next_is_highlight = False
  for idx,line in enumerate(lines):
    if line == "":
      continue # empty line
    elif line.startswith("@highlight"):
      next_is_highlight = True
    elif next_is_highlight:
      highlights.append(line)
    else:
      article_lines.append(line)
  # Make article into a single string
  article = ' '.join(article_lines)
  # Make abstract into a signle string, putting <s> and </s> tags around the sentences
  abstract = ' '.join(["%s %s %s" % (SENTENCE_START, sent, SENTENCE_END) for sent in highlights])
  return article, abstract


def write_to_bin(data_type, out_files, makevocab=False):
    """Read the tokenized txt files corresponding to the type(train/val/test) and writes them to a out_file."""
    print("Making bin file for data list in %s..." % data_type)

    num_data = num_of_data_pair # num_stories
    list_of_data = []
    num_of_train = 160000
    print(num_of_train)
    num_of_test = 20000
    print(num_of_test)
    num_of_val = 14846
    print(num_of_val)
    
    if (data_type == "train"):
        list_of_data = ["content" + str(i) + ".txt" for i in range(num_of_train)]
    elif (data_type == "test"):
        list_of_data = ["content" + str(i) + ".txt" for i in range(num_of_train, num_of_train + num_of_test)]
    elif (data_type == "val"):
        list_of_data = ["content" + str(i) + ".txt" for i in range(num_of_train, num_of_train + num_of_test + num_of_val)]
    else :
        print("data type error")

    
    if makevocab: # if data_type is "train"
        vocab_counter = collections.Counter()
    
    with open(out_files, 'wb') as writer:
        # for idx,s in enumerate(story_fnames): # fnames-[0, title] is all the name of the files 
        for idx,s in enumerate(list_of_data):
            if idx % 1000 == 0: # story_fnames contains hashed hex digit of the url + .story
                print("Writing data %i of %i; %.2f percent done" % (idx, num_data, float(idx)*100.0/float(num_data)))
            # Look in the tokenized story dirs to find the .story file corresponding to this url
            if os.path.isfile(os.path.join(content_tokenized_dir, s)): # 만약 content 데이터라면
                text_file = os.path.join(content_tokenized_dir, s) # text_file 의 경로는 content_tokenized_Serialized
            elif os.path.isfile(os.path.join(headline_tokenized_dir, s)): #
                text_file = os.path.join(headline_tokenized_dir, s)
            else: # error handling
                print("Error: Couldn't find tokenized text fils %s in either tokenized text directories %s and %s. Was there an error during tokenizing?" % (s, content_tokenized_dir, headline_tokenized_dir))
                # Check again if tokenized text directories contain correct number of files
                print("Checking that the tokenized text directories %s and %s contain correct number of files..." % (content_tokenized_dir, headline_tokenized_dir))
                check_num_data(content_tokenized_dir, num_data)
                check_num_data(headline_tokenized_dir, num_data)
                raise Exception("Tokenized texts directories %s and %s contain correct number of files but story file %s found in neither." % (content_tokenized_dir, headline_tokenized_dir, s))

            #Get the strings to write to .bin file
            article, abstract = get_art_abs(text_file)
            article = article.encode("utf-8")
            abstract = abstract.encode("utf-8")

            # Write to tf.Example - Serailization
            tf_example = example_pb2.Example()
            tf_example.features.feature['article'].bytes_list.value.extend([article])
            tf_example.features.feature['abstract'].bytes_list.value.extend([abstract])
            tf_example_str = tf_example.SerializeToString()
            str_len = len(tf_example_str)
            writer.write(struct.pack('q', str_len))
            writer.write(struct.pack('%ds' % str_len, tf_example_str))

            # Write the vocab to file, if applicable
            if makevocab:
                article = str(article)
                abstract = str(abstract)
                art_tokens = article.split(' ')
                abs_tokens = abstract.split(' ')
                abs_tokens = [t for t in abs_tokens if t not in [SENTENCE_START, SENTENCE_END]] # remove these tags from vocab
                tokens = art_tokens + abs_tokens
                tokens = [t.strip() for t in tokens] # strip
                tokens = [t for t in tokens if t!=""] # remove empty
                vocab_counter.update(tokens)

    print("Finishing writing file %s\n" % out_files)
    
    # write vocab to file
    if makevocab:
        print("Writing vocab file...")
        with open(os.path.join(finished_files_dir, "vocab"), 'w') as writer:
            for word, count in vocab_counter.most_common(VOCAB_SIZE):
                writer.write(word + ' ' + str(count) + '\n')
        print("Finished writing vocab file")


def chunk_file(set_name):
    in_file = 'finished_files/%s.bin' % set_name
    reader = open(in_file, "rb")
    chunk = 0
    finished = False
    while not finished:
        chunk_fname = os.path.join(chunks_dir, '%s_%03d.bin' % (set_name, chunk)) # new chunk
        with open(chunk_fname, 'wb') as writer:
            for _ in range(CHUNK_SIZE):
                len_bytes = reader.read(8)
                if not len_bytes:
                    finished = True
                    break
                str_len = struct.unpack('q', len_bytes)[0]
                example_str = struct.unpack('%ds' % str_len, reader.read(str_len))[0]
                writer.write(struct.pack('q', str_len))
                writer.write(struct.pack('%ds' % str_len, example_str))
            chunk += 1


def chunk_all():
  # Make a dir to hold the chunks
    if not os.path.isdir(chunks_dir):
        os.mkdir(chunks_dir)
  # Chunk the data
    for set_name in ['train', 'val', 'test']:
        print("Splitting %s data into chunks..." % set_name)
        chunk_file(set_name)
    print("Saved chunked data in %s" % chunks_dir)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("USAGE: python3 tokenize_data.py <content_dir> <headline_dir>")
        sys.exit()
    content_dir = sys.argv[1]
    headline_dir = sys.argv[2]

    set_num_of_data_pair(content_dir)

    # check the num of .txt files for each dir
    check_num_data(content_dir, num_of_data_pair)
    check_num_data(headline_dir, num_of_data_pair)

    # Create new directories to store tokenized data and finished data
    if not os.path.exists(content_tokenized_dir): os.makedirs(content_tokenized_dir)
    if not os.path.exists(headline_tokenized_dir): os.makedirs(headline_tokenized_dir)
    if not os.path.exists(finished_files_dir): os.makedirs(finished_files_dir)

    # Run stanford tokenizer on text based files, outputting to tokeinzed files directories
    tokenize_data(content_dir, content_tokenized_dir)
    tokenize_data(headline_dir, headline_tokenized_dir)

    type_train = "train"
    type_test = "test"
    type_val = "val"
    # Read the tokenized data, do a little postprocessing then write to bin files
    write_to_bin(type_test, os.path.join(finished_files_dir, "test.bin")) # write to bin files
    write_to_bin(type_val, os.path.join(finished_files_dir, "val.bin")) # write to bin files
    write_to_bin(type_train, os.path.join(finished_files_dir, "train.bin"), makevocab=True) # write to bin files with vocab files

    # Chunk the data. This splits each of train.bin, val.bin and test.bin into smaller chunks, each containing e.g. 1000 examples, and saves them in finished_files/chunks
    chunk_all()
