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

void uart_init()
{
    USICR &= ~(1 << USICS1);
    USICR &= ~(1 << USICS0);
}

void uart_puts(const char* string)
{
    while (*string != '\0')
    {
        USIDR = *string++;
        for (uint8_t i = 0; i < 8; i++)
        {
            USICR |= (1 << USICLK);
        }
    }
    USIDR = '\n';
    for (uint8_t i = 0; i < 8; i++)
    {
        USICR |= (1 << USICLK);
    }
}

uint8_t unsorted[] = {0x00, 0x20, 0x10, 0x30, 0x50, 0x40, 0x60, 0x70};
uint8_t long_unsorted[32];
int main(void)
{
    uart_init();
    uart_puts("Starting sort 1...");
    quicksort(unsorted, 0, sizeof(unsorted) / sizeof(uint8_t) - 1);
    uart_puts("Sort 1 done.");

    for (uint8_t i = 0; i < sizeof(unsorted) / sizeof(uint8_t) - 1; i++)
    {
        if (unsorted[i] > unsorted[i + 1])
        {
            uart_puts("Sort 1 error.");
        }
    }

    for (uint8_t i = 0; i < sizeof(long_unsorted) / sizeof(uint8_t); i++)
    {
        long_unsorted[i] = (sizeof(long_unsorted) / sizeof(uint8_t)) - i;
    }

    uart_puts("Starting sort 2...");
    quicksort(long_unsorted, 0, sizeof(long_unsorted) / sizeof(uint8_t) - 1);
    uart_puts("Sort 2 done.");

    for (uint8_t i = 0; i < sizeof(long_unsorted) / sizeof(uint8_t) - 1; i++)
    {
        if (long_unsorted[i] > long_unsorted[i + 1])
        {
            uart_puts("Sort 2 error.");
        }
    }

    uart_puts("All done.");

    return 0;
}
