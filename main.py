#!/usr/bin/python3
import regex

class Grid:

    def __init__(self, size):
        self.size = size
        self.nregex = self.size * 2 + 1
        self.grid = []
        row = lambda x: [regex.ReCharClass(include=False) for j in range(x)]
        for i in range(self.nregex):
            self.grid.append(row(self.size + 1 + self.updown(i)))

    def updown(self, i):
        return i - 2 * max(0, i - self.size)

    def iter_line(self, axis, pos):
        assert(axis in range(3) and pos in range(self.nregex))

        def f0(i):
            return pos, i
        def f1(i):
            s1 = min(pos + self.size, self.nregex - 1)
            y = self.nregex - 1 - max(0, pos - self.size) - i
            x = min(s1 - i, pos)
            return y, x
        def f2(i):
            s1 = self.nregex - 1 - max(0, pos - self.size)
            y = max(0, self.size - pos) + i
            x = min(s1 - i, self.nregex - 1 - pos)
            return y, x

        axis_method = [f0, f1, f2][axis]

        for i in range(self.size + 1 + self.updown(pos)):
            yield axis_method(i)

    def __getitem__(self, a):
        return self.grid[a[0]][a[1]]

    def __setitem__(self, a, val):
        self.grid[a[0]][a[1]] = val

    def copy(self):
        new_grid = Grid(self.size)
        for i, row in enumerate(self.grid):
            new_grid.grid[i] = [x for x in row]
        return new_grid

    def __eq__(self, o):
        return self.grid == o.grid

    def __str__(self):
        s = ""
        for i in range(self.nregex):
            s += " " * (1 + self.size - self.updown(i))
            s += " ".join(x.single_char() for x in self.grid[i]) + "\n"
        return s

class ReCrossword:

    def __init__(self):
        self.size = 0
        self.regex = [[] for i in range(3)]

    def read_from_file(self, fp):
        self.size = int(fp.readline())
        nregex = self.size * 2 + 1
        for i in range(3):
            fp.readline()
            self.regex[i] = [regex.Regex(fp.readline().strip()) for j in range(nregex)]

        self.grid = Grid(self.size)

    def write_to_file(self, fp=None):
        print(self.grid, file=fp)

    def solve(self):
        for b in range(10):
            prev_grid = self.grid.copy()
            for i in range(3):
                for j, re in enumerate(self.regex[i]):
                    grid_iter = list(self.grid.iter_line(i, j))
                    line = [self.grid[x] for x in grid_iter]
                    new_vals = re.fixed_values(line)
                    #print(*[a.single_char() for a in new_vals])
                    for a, x in zip(new_vals, grid_iter):
                        self.grid[x] = a

            #print(self.grid)

            if self.grid == prev_grid:
                return




if __name__ == '__main__':
    import sys

    re_cross = ReCrossword()
    fp = open(sys.argv[1])
    re_cross.read_from_file(fp)
    fp.close()

    re_cross.solve()
    re_cross.write_to_file()
