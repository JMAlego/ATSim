#include <avr/io.h>
#include <stdint.h>

uint8_t partition(uint8_t to_sort[], uint8_t low, uint8_t high)
{
    uint8_t pivot = to_sort[high];
    uint8_t i = low;
    uint8_t temp;
    for (uint8_t j = low; j < high; j++)
    {
        if (to_sort[j] < pivot)
        {
            temp = to_sort[i];
            to_sort[i] = to_sort[j];
            to_sort[j] = temp;
            i++;
        }
    }
    temp = to_sort[i];
    to_sort[i] = to_sort[high];
    to_sort[high] = temp;
    return i;
}

void quicksort(uint8_t to_sort[], uint8_t low, uint8_t high)
{
    if (low < high)
    {
        uint8_t partition_point = partition(to_sort, low, high);
        if (partition_point > low)
            quicksort(to_sort, low, partition_point - 1);
        quicksort(to_sort, partition_point + 1, high);
    }
}

uint8_t unsorted[] = {0x00, 0x20, 0x10, 0x30, 0x50, 0x40, 0x60, 0x70};
int main(void)
{
    quicksort(unsorted, 0, 7);

    for (uint8_t i = 0; i < sizeof(unsorted) / sizeof(uint8_t) - 1; i++)
    {
        if (unsorted[i] > unsorted[i + 1])
        {
            // break if not sorted
            __asm("break");
        }
    }

    return 0;
}
