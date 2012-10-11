"""
snakenest.py
(Python 3.2.3)
Parser for answer set programs (ASP) written in Python. Specialized for the
output of clingo (from Potassco Labs).

Example run (see test.py):

  clingo example.lp -n 3 > out.as
  python3
  import snakenest
  with open("out.as") as fin:
    raw = fin.read()
  answers = snakenest.parse_raw(raw)

"""

def trace(*args, **kwargs):
  """
  Uncomment this to print some trace messages.
  """
  #print(*args, **kwargs)
  pass

rawline = 0
quotecontext = 5

def parse_raw(raw):
  """
  parse
  Takes a raw string (assumed to be the output of clingo) and parses it to
  return a list of answer sets (each of which is an AnswerSet object). If the
  input is the result of an unsatisfiable program, an empty list is returned.
  If there's an error, an exception is raised, and if it's ignored, None is
  returned.
  """
  global rawline
  lines = raw.split('\n')
  sets = []
  results = lines[-8:]
  lines = lines[:-8]
  indicator = results[0]
  if indicator == "UNSATISFIABLE":
    return sets
  elif indicator != "SATISFIABLE":
    raise ValueError(
      """\
Can't figure out what the solution status is (did clingo fail with an error?).
Indicator line is:
  {}
""".format(indicator)
    )
    return None
  answernum = 0
  for l in lines:
    rawline += 1
    if l.startswith("Answer:"):
      answernum = int(l[7:])
      continue
    else:
      sets.append(parse_set(l, answernum))
  return sets

def parse_set(line, set_number=0):
  """
  Takes a single line representing an answer set and parses it into an
  AnswerSet object. It also takes an optional set number and sets the
  "set_number" property of the returned AnswerSet to that number.
  """
  pcount = 0
  predicates = []
  if not line:
    ret = AnswerSet()
    ret.set_number = set_number
    return ret
  tail = line
  while tail:
    term, tail = scan(tail, ' ')
    predicate = parse_predicate(term)
    pcount += 1
    trace("Predicates processed: {}".format(pcount), end='\r')
    predicates.append(predicate)
  ret = AnswerSet(predicates)
  ret.set_number = set_number
  return ret

def parse_predicate(term):
  """
  Recursively parses a single term.
  """
  # Scan the name:
  name, tail = scan(term, '(')
  name = intended_name(name)
  if not tail:
    return Predicate(name=name)
  if tail[-1] != ')':
    raise ValueError(
      "Malformed predicate '{}': missing closing ')' [line {}].".format(
        term,
        rawline
      )
    )
  children = parse_children(tail[:-1])
  return Predicate(name=name, children=children)

def parse_children(tail):
  """
  Takes a parameter list with an extra closing paren at the end and parses
  it recursively into a list of child predicates.
  """
  child, tail = scan(tail, ',', honorparens=True)
  if not tail:
    return [parse_predicate(child)]
  rest = parse_children(tail)
  return [parse_predicate(child)] + rest

def scan(text, target, honorquotes=True, honorparens=False):
  """
  Scans some text to find the next instance of the target character, and
  returns a tuple containing the text up to that character and the text
  following that character (the character itself is not in either string). If
  the character is not found, it returns a tuple containing the complete text
  and None.

  While scanning, it understands quoted strings and backslash escapes, and
  instances of the target character that are quoted or escaped are ignored. If
  honorquotes is False, it will ignore quotes and match the target inside them,
  likewise if honorparens is true, it won't find the target unless it is
  outside of any (potentially nested) parens.
  
  Note that setting the target to either '"' or '('/')' when honorquotes or
  honorparens (respectively) is on will result in a ValueError.
  """
  if not text:
    return '', None
  if target == '"' and honorquotes:
    raise ValueError("Can't search for and honor quotes at the same time.")
  if target in '()' and honorparens:
    raise ValueError("Can't search for and honor parentheses at the same time ")
  inquote = False
  escaped = False
  end = 0
  pdepth = 0
  lastquote = None
  for i, c in enumerate(text):
    end = i
    if escaped:
      escaped = False
      continue
    if c == '\\':
      escaped = True
    elif c == '"' and honorquotes:
      inquote = not inquote
      lastquote = i
    elif c == '(' and honorparens and not inquote:
      pdepth += 1
    elif c == ')' and honorparens and not inquote:
      pdepth -= 1
      if pdepth < 0:
        raise ValueError("""\
Mismatched parens (extra closing paren) [line {}]. Context:
{}
""".format(rawline, text[:i+1])
        )
    elif c == target and not inquote and pdepth == 0:
      break
  if inquote:
    raise ValueError(
      "Mismatched quotes! This quote: '{}' never ended [line {}].".format(
        text[max(0, lastquote-quotecontext):lastquote+quotecontext],
        rawline
      )
    )
  if pdepth != 0:
    raise ValueError("""\
Mismatched parens (missing closing paren(s)) [line {}]. Context:
{}
""".format(rawline, text[:i+1])
    )
  if text[end] == target:
    return text[:end], text[end+1:]
  else:
    assert(i == len(text) - 1)
    return text, None

def intended_name(name):
  """
  Strips out quoted strings from a name and replaces them with their raw
  versions. So for example, if

    foo"()\\"\\\\"bar

  is passed in, the result will be:

    foo()"\\bar

  Literal backslashes and escaped quotes are the only escape characters
  understood.
  """
  result = ""
  inquote = False
  escaped = False
  lastquote = None
  for i, c in enumerate(name):
    if escaped:
      escaped = False
      if c == '\\':
        result += '\\'
      elif c == '"':
        result += '"'
      else:
        result += '\\' + c
    elif c == '\\':
      escaped = True
    elif c == '"':
      inquote = not inquote
      lastquote = i
    else:
      result += c
  if inquote:
    raise ValueError(
        "Mismatched quotes! This quote: '{}' never ended [line {}].".format(
        text[max(0, lastquote-quotecontext):lastquote+quotecontext],
        rawline
      )
    )
  return result

class AnswerSet:
  """
  Represents a set of predicates. Caches them by their names (and also by the
  names of their children) to enable quick lookups. Indexes are created when
  the answer set is created, and as needed for new answer sets returned by
  lookups. Iterating through the set will yield predicates in the order they
  were in when passed to the constructor, but for subsets returned via
  lookup(), this ordering is not preserved.
  """
  def __init__(self, predicates=None):
    predicates = predicates or ()
    self._predicates = tuple(predicates)
    self._byname = {}
    self._bystrings = {}
    for p in self._predicates:
      if p.name in self._byname:
        self._byname[p.name].append(p)
      else:
        self._byname[p.name] = [p]
      for s in p.strings:
        if s in self._bystrings:
          self._bystrings[s].append(p)
        else:
          self._bystrings[s] = [p]

  @property
  def predicates(self):
    return self._predicates

  def __str__(self):
    return ' '.join(str(p) for p in self._predicates)

  def __len__(self):
    return len(self._predicates)

  def __hash__(self):
    return (hash(self._predicates) * 3) + 379

  def __eq__(self, other):
    return self._predicates == other._predicates

  def __ne__(self, other):
    return self._predicates != other._predicates

  def __contains__(self, item):
    return item in self._predicates

  def __iter__(self):
    for p in self._predicates:
      yield p
    raise StopIteration

  def is_empty(self):
    return len(self._predicates) == 0

  def lookup(self, name, anynested=False, fuzzy=False):
    """
    Looks up the given predicate name and returns all predicates from the
    answer set whose name matches exactly.
    
    If anynested is True, it searches nested predicates as well, so for example
    a predicate "bar(foo)." will match a search for either "foo" or "bar" if
    anynested is True, but will only match a search for "bar" if anynested is
    false.

    If fuzzy is True, it will match predicates that merely contain the search
    term, rather than only exact matches. So a predicate "baz." will match
    any of "b", "ba", "az", or "baz" (but not "bz") if fuzzy is True.

    When fuzzy and anynested are both true, note that only individual names are
    searched. So for example, given a predicate "bar(foo)." with both anynested
    and fuzzy True, a search of "r(f" WILL NOT match. This is because the
    search uses the index, which is built from individual predicate names, and
    the text version of the predicate isn't stored anywhere.
    """
    lookin = self._byname
    if anynested:
      lookin = self._bystrings
    if fuzzy:
      matched = []
      for test in lookin:
        if name in test:
          matched.extend(lookin[test])
      return AnswerSet(matched)
    else:
      if name in lookin:
        return AnswerSet(lookin[name])
      else:
        return AnswerSet()

class Predicate:
  """
  Represents a predicate which can have any (fixed) arity, and which maintains
  a list of "children" predicates that describe its arguments.
  """
  _arity = 0
  def __init__(self, name, children=None):
    self._name = name
    children = children or ()
    self._children = tuple(children)
    self._arity = len(self.children)
    self._strings = { self._name }
    for c in self.children:
        self._strings |= c._strings

  def __str__(self):
    name = self._name
    if  ' ' in self._name\
     or '(' in self._name\
     or ')' in self._name\
     or '\\' in self._name\
     or '"' in self._name:
      name='"{}"'.format(self._name.replace('\\', '\\\\').replace('"', '\\"'))
    if self._children:
      return "{name}({children})".format(
        name=name,
        children=','.join(str(c) for c in self.children)
      )
    else:
      return name

  @property
  def name(self):
    "This predicate's name."
    return self._name

  @property
  def children(self):
    "This predicate's parameters."
    return self._children

  @property
  def arity(self):
    "This predicate's arity."
    return self._arity

  @property
  def strings(self):
    """
    A set of strings that contains the names of each predicate nested inside
    this one as well as the name of this predicate (without repeats obviously).
    """
    return self._strings

  def __len__(self):
    return self.arity

  def __getitem__(self, key, value):
    if key in range(self.arity):
      return self.children[key]
    elif type(key) == int:
      raise IndexError("Index out of range: {}".format(key))
    else:
      raise TypeError("Index isn't an integer: {}".format(key))

  def __hash__(self):
    return (hash(self.name) + 23) ^ hash(self.children)

  def __eq__(self, other):
    return self.name == other.name and self.children == other.children

  def __ne__(self, other):
    return self.name != other.name or self.children != other.children
