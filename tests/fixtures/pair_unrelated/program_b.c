#include <stdio.h>

void multiply_matrices(int first[10][10], int second[10][10], int result[10][10], int r1, int c1, int r2, int c2) {
    for (int i = 0; i < r1; ++i) {
        for (int j = 0; j < c2; ++j) {
            result[i][j] = 0;
            for (int k = 0; k < c1; ++k) {
                result[i][j] += first[i][k] * second[k][j];
            }
        }
    }
}

int main() {
    int mat1[10][10] = {{1, 2}, {3, 4}};
    int mat2[10][10] = {{5, 6}, {7, 8}};
    int res[10][10];
    multiply_matrices(mat1, mat2, res, 2, 2, 2, 2);
    return 0;
}
