import numpy as np
from pathlib import Path


class FileOperationsMixin:
    def save_to_file(self, filename):
        Path(filename).write_text(str(self))


class PrintMixin:
    def __str__(self):
        return np.array_str(self.data, precision=2, suppress_small=True)


class AccessorsMixin:
    @property
    def shape(self):
        return self.data.shape

    @property
    def T(self):
        return self.__class__(self.data.T)


class Matrix(FileOperationsMixin, PrettyPrintMixin, AccessorsMixin):
    def __init__(self, data):
        self.data = np.array(data)

    def __add__(self, other):
        return self.__class__(self.data + other.data)

    def __sub__(self, other):
        return self.__class__(self.data - other.data)

    def __mul__(self, other):
        return self.__class__(self.data * other.data)

    def __matmul__(self, other):
        return self.__class__(self.data @ other.data)

    def __truediv__(self, other):
        return self.__class__(self.data / other.data)

    def __pow__(self, power):
        return self.__class__(self.data ** power)


if __name__ == '__main__':
    np.random.seed(0)
    m1 = Matrix(np.random.randint(0, 10, (10, 10)))
    m2 = Matrix(np.random.randint(0, 10, (10, 10)))

    (m1 + m2).save_to_file('matrix_add_2.txt')
    (m1 * m2).save_to_file('matrix_multiply_2.txt')
    (m1 @ m2).save_to_file('matrix_math_multiply_2.txt')
