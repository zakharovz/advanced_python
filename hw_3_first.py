import numpy as np


class Matrix:
    def __init__(self, data):
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0]) if self.rows > 0 else 0

        for row in data:
            if len(row) != self.cols:
                raise ValueError("Длина рядов должна совпадать")

    def __add__(self, other):
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Размерности матриц не согласованы")

        result = [
            [self.data[i][j] + other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ]
        return Matrix(result)

    def __mul__(self, other):
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Размерности матриц не согласованы")

        result = [
            [self.data[i][j] * other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ]
        return Matrix(result)

    def __matmul__(self, other):
        if self.cols != other.rows:
            raise ValueError("Размерности матриц не согласованы")

        result = [
            [
                sum(self.data[i][k] * other.data[k][j] for k in range(self.cols))
                for j in range(other.cols)
            ]
            for i in range(self.rows)
        ]
        return Matrix(result)

    def __str__(self):
        return '\n'.join([' '.join(map(str, row)) for row in self.data])


if __name__ == '__main__':
    np.random.seed(0)
    matrix1_data = np.random.randint(0, 10, (10, 10)).tolist()
    matrix2_data = np.random.randint(0, 10, (10, 10)).tolist()

    matrix1 = Matrix(matrix1_data)
    matrix2 = Matrix(matrix2_data)

    try:
        add_result = matrix1 + matrix2
        with open('matrix_add.txt', 'w') as f:
            f.write(str(add_result))

        mul_result = matrix1 * matrix2
        with open("""matrix_multiply.txt""", 'w') as f:
            f.write(str(mul_result))

        matmul_result = matrix1 @ matrix2
        with open('matrix_math_multiply.txt', 'w') as f:
            f.write(str(matmul_result))
    except ValueError as e:
        print(f"Error: {e}")


