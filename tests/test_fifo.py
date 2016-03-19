from __future__ import unicode_literals
from zerotk.terraformer.fifo import FIFO



#===================================================================================================
# Test
#===================================================================================================
class Test:

    def testFifo(self):
        fifo = FIFO(2)
        fifo[1] = 1
        fifo[2] = 2
        fifo[3] = 3

        assert fifo.keys() == [2, 3]

        _a = fifo[2]
        # Nothing changes
        assert fifo.keys() == [2, 3]

        fifo[2] = 2
        assert fifo.keys() == [3, 2]
