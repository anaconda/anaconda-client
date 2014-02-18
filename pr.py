from numpy import *

class PageRank(object):
    def __init__(self, documents, graph, d = 0.85, steps = 15):
        self._link_matrix = mat(0)
        self._documents   = documents
        self._page_ranks  = []
        self._dampening   = d

        self.setup(documents, graph)
        print "STEP(0)"
        print str(self._page_ranks)
        print str(self._link_matrix)
        print "\n"

        for i in range(steps):
            self.convergence_step()
            print "STEP(" + str(i+1) + ")"
            for doc,pr in zip(self._documents, self._page_ranks):
                print doc, pr
            print str(self._link_matrix)
            print "\n"

    def setup(self, documents, graph):
        _matrix = []

        for document in documents:
            _num_documents = len(graph[document])
            _probability   = 1 / float(_num_documents)
            _row           = []

            for link in documents:
                if link in graph[document]:
                    _row.append(_probability)
                else:
                    _row.append(0)
            _matrix.append(_row)
            self._page_ranks.append(_probability)

        self._link_matrix = mat(_matrix).transpose()
        self._link_matrix /= self._link_matrix.sum()

    def update(self):
        for p in range(len(self._page_ranks)):
            for i in range(len(self._documents)):
                if self._link_matrix[p,i] > 0:
                    self._link_matrix[p,i] = self._page_ranks[i]

    def calculate(self, document):
        print "calculate", document
        backlinks = self._link_matrix[document]
        print "backlinks", backlinks
        backlinks = sum(backlinks)
        page_rank = (1 - self._dampening) + (self._dampening*(backlinks))
        print 'page_rank', page_rank
        self._page_ranks[document] = page_rank
        return page_rank

    def convergence_step(self):
        for document in range(len(self._documents)):
            self.calculate(document)
        self.update()

    def page_rank(self):
       return self._page_ranks

documents = ["A", "B", "C"]
graph     = {
                "A": ["B"],
                "B": ["C", "A"],
                "C": ["A"],
            }

pr = PageRank(documents, graph)
print str(pr.page_rank())

#917004895LL