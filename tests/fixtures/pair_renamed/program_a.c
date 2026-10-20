#include <stdio.h>

/*
 * Implementation of Bubble Sort in C
 * Sorts an integer array in ascending order
 */
void bubble_sort(int numbers[], int count) {
    int outer_idx, inner_idx, temp_val;
    for (outer_idx = 0; outer_idx < count - 1; outer_idx++) {
        // Track whether any swaps took place
        int swapped = 0;
        for (inner_idx = 0; inner_idx < count - outer_idx - 1; inner_idx++) {
            if (numbers[inner_idx] > numbers[inner_idx + 1]) {
                temp_val = numbers[inner_idx];
                numbers[inner_idx] = numbers[inner_idx + 1];
                numbers[inner_idx + 1] = temp_val;
                swapped = 1;
            }
        }
        if (swapped == 0) {
            break;
        }
    }
}

int main() {
    int dataset[] = {64, 34, 25, 12, 22, 11, 90};
    int len = sizeof(dataset) / sizeof(dataset[0]);
    bubble_sort(dataset, len);
    printf("Sorted array: ");
    for (int k = 0; k < len; k++) {
        printf("%d ", dataset[k]);
    }
    printf("\n");
    return 0;
}
