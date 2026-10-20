#include <stdio.h>

void sort_elements(int arr[], int total) {
    int i, j, aux;
    for (i = 0; i < total - 1; i++) {
        int has_swapped = 0;
        for (j = 0; j < total - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                aux = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = aux;
                has_swapped = 1;
            }
        }
        if (has_swapped == 0) {
            break;
        }
    }
}

int main() {
    int items[] = {64, 34, 25, 12, 22, 11, 90};
    int size = sizeof(items) / sizeof(items[0]);
    sort_elements(items, size);
    printf("Sorted array: ");
    for (int p = 0; p < size; p++) {
        printf("%d ", items[p]);
    }
    printf("\n");
    return 0;
}
