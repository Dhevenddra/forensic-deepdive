#ifndef MATHUTIL_H
#define MATHUTIL_H

typedef struct Vector {
    int x;
    int y;
} Vector;

enum Sign {
    NEGATIVE,
    ZERO,
    POSITIVE
};

int add(int a, int b);
int multiply(int a, int b);

#endif
