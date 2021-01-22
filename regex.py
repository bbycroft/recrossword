#!/usr/bin/python3

"""
TODO: make all of this a bit nicer. It was quite a rushed job.

TODO: make sure back-references can be modified by ref (somehow).
That way their constraints are fully satisfied.
"""

class Regex:

    def __init__(self, string):
        self.seq = ReSequence.parse(TokenStream(string))

    def all_matches(self, string):
        matcher = Matcher(string)
        partial = PartialMatch(matcher)

        all_matches = self.seq.all_matches(partial)

        full_matches = [a.partial for a in all_matches
                        if len(a.partial) == len(string)]

        return full_matches

    def possible_changes(self, string):
        matches = self.all_matches(string)

        # or'ing the matches together
        combined = [ReCharClass() for a in range(len(string))]
        for match in matches:
            combined = [c | m for c, m in zip(combined, match)]

        return combined

    def fixed_values(self, string):
        changes = self.possible_changes(string)

        # and'ing the matches with the original
        result = [s & ch for (s, ch) in zip(string, changes)]

        return result

    def __repr__(self):
        return str(self.seq)

"""
The all_matches() method takes a single PartialMatch object, and returns
an iterator with all valid PartialMatch's.

"""

class Matcher:
    """
    This class contains global state of a single match operation.
    It contains the results of any complete matches, and also a cache
    for dynamic programming.
    """
    def __init__(self, string):
        self.string = [ReCharClass(s) for s in string]
        self.cache = {}
        self.count = 0

class PartialMatch:
    """
    Instances of this class represent a valid partial match.

    There are typically many instances of this class in a single match
    operation.

    This class should be treated as immutable, and changes should be made
    via the with_* methods, which return a new reference.
    """
    def __init__(self, matcher, partial=[], groups=[]):
        self.matcher = matcher # ref to 'global'
        self.partial = partial
        self.groups = groups

        if len(self.partial) == len(self.matcher.string):
            self.matcher.count += 1

    def copy(self):
        return PartialMatch(self.matcher, self.partial, self.groups)

    def curr(self):
        if len(self.partial) >= len(self.matcher.string):
            return ReCharClass("", include=True)
        return self.matcher.string[len(self.partial)]

    def with_match(self, val):
        new_partial = self.copy()
        new_partial.partial = new_partial.partial + [val]
        return new_partial

    def with_group(self, group_idx, group_start):
        new_partial = self.copy()
        new_partial.groups = dict(self.groups)
        new_partial.groups[group_idx] = (len(self.partial) - group_start,
                [group_start])
        print(new_partial.groups)
        return new_partial

    def with_backref(self, group_idx):
        # should be called after groups[group_idx][0] calls to with_match
        print("with_backref called")
        new_partial = self.copy()
        group_len, starts = new_partial.groups[group_idx]
        starts = starts + [len(self.partial) - group_len]
        new_partial.groups[group_idx] = (group_len, starts)
        return new_partial

    def get_group(self, i):
        group_len, starts = self.groups[i]
        combined = self.partial[starts[0]:starts[0]+group_len]
        for s in starts:
            group = self.matcher.string[s:s+group_len]
            combined = [c & g for c, g in zip(combined, group)]
        for s in starts:
            self.partial[s:s+group_len] = combined
        return combined

    def __repr__(self):

        return "P[" + ",".join(str(x) for x in self.partial) + "]"

class TokenStream:

    def __init__(self, string):
        self.string = string
        self.pos = 0
        self.group_counter = 0

    def end(self):
        return self.pos >= len(self.string)

    def peek(self):
        if self.end(): return ""
        else: return self.string[self.pos]

    def pop(self):
        token = self.peek()
        self.pos += 1
        return token

    def pop_if_exists(self, x):
        if self.peek() == x:
            self.pop()
            return True
        else:
            return False
    
    def get_next_group(self):
        self.group_counter += 1
        return self.group_counter

class ReAlternative:

    def __init__(self, objs=[]):
        self.objs = objs

    def all_matches(self, partial):
        for o in self.objs:
            for p in o.all_matches(partial):
                yield p

    def __repr__(self):
        return "|".join(str(x) for x in self.objs)

class ReSequence:

    def __init__(self, objs=[], group_idx=None):
        self.objs = objs
        self.group_idx = group_idx

    @classmethod
    def parse(cls, tokens):
        alternatives = []
        sequence = []
        while not tokens.end() and tokens.peek() != ")":
            if tokens.peek() in "{}]$*+?":
                raise RuntimeError()
            elif tokens.pop_if_exists("|"):
                assert(len(sequence))
                alternatives.append(sequence)
                sequence = []
            else:
                sequence.append(ReRepetition.parse(tokens))

        if len(alternatives):
            alternatives.append(sequence)
            alternatives = [ReSequence(x) for x in alternatives]
            return ReAlternative(alternatives)
        else:
            return ReSequence(sequence)

    def create_group(self, partial, start):
        x = ReSequence(partial.matcher.string[start:len(partial.partial)])
        return (x, start)

    def all_matches(self, partial, pos=0, group_start=0):
        if pos == 0 and self.group_idx is not None:
            group_start = len(partial.partial)

        if pos >= len(self.objs):
            if self.group_idx is not None:
                partial = partial.with_group(self.group_idx, group_start)
            yield partial
        else:
            #print("seq:", partial)
            for p in self.objs[pos].all_matches(partial):
                for x in self.all_matches(p, pos + 1, group_start):
                    yield x

    def __repr__(self):
        return "".join(str(x) for x in self.objs)


class ReRepetition:

    def __init__(self, obj, repeat):
        self.obj = obj
        self.repeat = repeat

    @classmethod
    def parse(cls, tokens):
        if tokens.pop_if_exists("("):
            obj = ReSequence.parse(tokens)
            obj.group_idx = tokens.get_next_group()
            assert(tokens.pop() == ")")
        else:
            obj = ReCharClass.parse(tokens)

        if tokens.peek() in "{*+?":
            repeat = ReRepeat.parse(tokens)
        else:
            repeat = ReRepeat()
        
        return ReRepetition(obj, repeat)

    def all_matches(self, partial, count=0):
        if count in self.repeat: # in the repetition
            yield partial
            if count + 1 not in self.repeat: # too many
                return
        
        #print("rep:", partial)
        for p in self.obj.all_matches(partial):
            for x in self.all_matches(p, count + 1):
                yield x

    def __repr__(self):
        if not isinstance(self.obj, (ReCharClass, ReBackRef)):
            s = "({})".format(str(self.obj))
        else:
            s = str(self.obj)
        return s + str(self.repeat)

class ReCharClass:
    """
    [abc] => (chars="abc", include=True)
    [^abc] => (chars="abc", include=False)
    . => (chars="", include=False)
    """

    def __init__(self, chars=set(), include=True):
        if isinstance(chars, ReCharClass):
            self.chars = chars.chars
            self.include = chars.include
        else:
            self.chars = set(chars)
            self.include = include

    def __and__(self, c):
        """
        returns a charclass that will match against both this charclass *and*
        the provided charclass.
        """
        assert(isinstance(c, ReCharClass))

        if self.include and c.include:
            return ReCharClass(self.chars & c.chars)
        elif self.include and not c.include:
            return ReCharClass(self.chars - c.chars)
        elif not self.include and c.include:
            return ReCharClass(c.chars - self.chars)
        else:
            return ReCharClass(c.chars | self.chars, include=False)

    def __or__(self, c):
        """
        returns a charclass that will match against either this charclass *or*
        the provided charclass.
        """
        assert(isinstance(c, ReCharClass))

        if self.include and c.include:
            return ReCharClass(self.chars | c.chars)
        elif self.include and not c.include:
            return ReCharClass(c.chars - self.chars, include=False)
        elif not self.include and c.include:
            return ReCharClass(self.chars - c.chars, include=False)
        else:
            return ReCharClass(self.chars & c.chars, include=False)

    def __eq__(self, o):
        return self.chars == o.chars and self.include == o.include

    def match(self):
        return not self.include or len(self.chars) != 0


    @classmethod
    def parse(cls, tokens):
        if tokens.pop_if_exists("["):
            return cls.parse_in_brackets(tokens)

        if tokens.pop_if_exists("\\"):
            if tokens.peek().isdigit():
                return ReBackRef(int(tokens.pop()))
            else:
                return ReCharClass(tokens.pop())

        if tokens.pop_if_exists("."):
            return ReCharClass("", include=False)

        return ReCharClass(tokens.pop())

    @classmethod
    def parse_in_brackets(cls, tokens):
        chars = ""
        include = not tokens.pop_if_exists("^")
        while not tokens.pop_if_exists("]"):
            if tokens.pop_if_exists("\\"):
                chars += tokens.pop()
            elif tokens.peek() in "-^$":
                raise RuntimeError("unsupported token '{}' in char class"
                        .format(tokens.peek()))
            else:
                chars += tokens.pop()
        return ReCharClass(chars, include)

    def all_matches(self, partial):
        combined = self & partial.curr()

        c = partial.curr()

        if combined.match():
            yield partial.with_match(self)

    def __repr__(self):
        if len(self.chars) == 0:
            return "#" if self.include else "."
        elif len(self.chars) == 1 and self.include:
            return "".join(self.chars)
        caret = "" if self.include else "^"
        return "[" + caret + "".join(sorted(self.chars)) + "]"

    def single_char(self):
        if self.include:
            if len(self.chars) == 0:
                return "#"
            elif len(self.chars) == 1:
                return "".join(self.chars)
        return "."

class ReRepeat:
    """
    inclusive range (at both ends). A hi of None indicates no limit
     => (lo=1, hi=1)
    * => (lo=0, hi=None)
    + => (lo=1, hi=None)
    ? => (lo=0, hi=1)
    {n} => (lo=n, hi=n)
    {n,m} => (lo=n, hi=m)
    """

    def __init__(self, lo=1, hi=1):
        self.lo = lo
        self.hi = hi
        assert(self.lo is not None)
        assert(self.lo in self)

    def __contains__(self, x):
        return x >= self.lo and (self.hi is None or x <= self.hi)

    def compare(self, x):
        if x < self.lo: return -1
        if self.hi is not None and x > self.hi: return 1
        return 0

    @classmethod
    def parse(self, tokens):
        if tokens.pop_if_exists("?"):
            return ReRepeat(0, 1)
        elif tokens.pop_if_exists("*"):
            return ReRepeat(0, None)
        elif tokens.pop_if_exists("+"):
            return ReRepeat(1, None)
        else:
            return ReRepeat()

    def __repr__(self):
        if self.lo == 1 and self.hi == 1: return ""
        if self.lo == 0 and self.hi == 1: return "?"
        elif self.lo == 0 and self.hi is None: return "*"
        elif self.lo == 1 and self.hi is None: return "+"
        elif self.hi is None: return "{{{},}}".format(self.lo)
        elif self.lo == self.hi: return "{{{}}}".format(self.lo)
        else: return "{{{},{}}}".format(self.lo)

class ReBackRef:

    def __init__(self, position):
        self.position = position

    def all_matches(self, partial):
        sequence = partial.get_group(self.position)

        print("backref match:", sequence)

        for i, s in enumerate(sequence):
            combined = s & partial.curr()
            #print("seq[i], cur:", s, partial.curr(), combined)
            if not combined.match():
                return
            partial = partial.with_match(combined)

        yield partial.with_backref(self.position)

    def __repr__(self):
        return "\\{}".format(self.position)

if __name__ == "__main__":
    import sys
    r1 = Regex(sys.argv[1])
    print(r1)
    print("matches:", r1.all_matches(sys.argv[2]))

