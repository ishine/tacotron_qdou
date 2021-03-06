/*
 *	complex.c
 *        coded by H. Banno
 *
 *	Tomoki Toda (tomoki.toda@atr.co.jp)
 *			From Mar. 2001 to Sep. 2003
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#include "defs.h"
#include "memory.h"
#include "vector.h"
#include "voperate.h"
#include "complex.h"

FCOMPLEX xfcalloc(long length)
{
    FCOMPLEX cplx;

    length = MAX(length, 0);
    cplx = xalloc(1, struct FCOMPLEX_STRUCT);
    cplx->real = xfvalloc(length);
    cplx->imag = xfvalloc(length);
    cplx->length = length;

    return cplx;
}

FCOMPLEX xfczeros(long length)
{
    FCOMPLEX cplx;

    length = MAX(length, 0);
    cplx = xalloc(1, struct FCOMPLEX_STRUCT);
    cplx->real = xfvzeros(length);
    cplx->imag = xfvzeros(length);
    cplx->length = length;

    return cplx;
}

void xfcfree(FCOMPLEX cplx)
{
    if (cplx != NULL) {
	if (cplx->real != NODATA) {
	    xfvfree(cplx->real);
	}
	if (cplx->imag != NODATA) {
	    xfvfree(cplx->imag);
	}
	xfree(cplx);
    }

    return;
}

void fccopy(FCOMPLEX cplx, FVECTOR real, FVECTOR imag)
{
    if (real != NODATA) {
	fvcopy(cplx->real, real);
    }
    if (imag != NODATA) {
	fvcopy(cplx->imag, imag);
    }

    return;
}

FCOMPLEX xfccreate(FVECTOR real, FVECTOR imag, long length)
{
    FCOMPLEX cplx;

    cplx = xfczeros(length);
    fccopy(cplx, real, imag);

    return cplx;
}

DCOMPLEX xdcalloc(long length)
{
    DCOMPLEX cplx;

    length = MAX(length, 0);
    cplx = xalloc(1, struct DCOMPLEX_STRUCT);
    cplx->real = xdvalloc(length);
    cplx->imag = xdvalloc(length);
    cplx->length = length;

    return cplx;
}

DCOMPLEX xdczeros(long length)
{
    DCOMPLEX cplx;

    length = MAX(length, 0);
    cplx = xalloc(1, struct DCOMPLEX_STRUCT);
    cplx->real = xdvzeros(length);
    cplx->imag = xdvzeros(length);
    cplx->length = length;

    return cplx;
}

void xdcfree(DCOMPLEX cplx)
{
    if (cplx != NULL) {
	if (cplx->real != NODATA) {
	    xdvfree(cplx->real);
	}
	if (cplx->imag != NODATA) {
	    xdvfree(cplx->imag);
	}
	xfree(cplx);
    }

    return;
}

void dccopy(DCOMPLEX cplx, DVECTOR real, DVECTOR imag)
{
    if (real != NODATA) {
	dvcopy(cplx->real, real);
    }
    if (imag != NODATA) {
	dvcopy(cplx->imag, imag);
    }

    return;
}

DCOMPLEX xdccreate(DVECTOR real, DVECTOR imag, long length)
{
    DCOMPLEX cplx;

    cplx = xdczeros(length);
    dccopy(cplx, real, imag);

    return cplx;
}

DVECTOR xdcpower(DCOMPLEX cplx)
{
    long k;
    DVECTOR vec;

    vec = xdvalloc(cplx->length);

    for (k = 0; k < vec->length; k++) {
	vec->data[k] = SQUARE(cplx->real->data[k]) + SQUARE(cplx->imag->data[k]);
    }

    return vec;
}

DVECTOR xdcabs(DCOMPLEX cplx)
{
    long k;
    double value;
    DVECTOR vec;

    vec = xdvalloc(cplx->length);

    for (k = 0; k < vec->length; k++) {
	value = SQUARE(cplx->real->data[k]) + SQUARE(cplx->imag->data[k]);
	vec->data[k] = sqrt(value);
    }

    return vec;
}

DVECTOR xdvcpower(DVECTOR real, DVECTOR imag, long length)
{
    long k;
    DVECTOR y;
    
    y = xdvalloc(length);
    
    for (k = 0; k < y->length; k++) {
	y->data[k] = SQUARE(real->data[k]) + SQUARE(imag->data[k]);
    }
    
    return y;
}

DVECTOR xdvcabs(DVECTOR real, DVECTOR imag, long length)
{
    long k;
    double value;
    DVECTOR y;
    
    y = xdvalloc(length);
    
    for (k = 0; k < y->length; k++) {
	value = SQUARE(real->data[k]) + SQUARE(imag->data[k]);
	y->data[k] = sqrt(value);
    }
    
    return y;
}

DCOMPLEX xdvcexp(DVECTOR real, DVECTOR imag, long length)
{
    long k;
    double rx;
    DCOMPLEX cplx;

    cplx = xdcalloc(length);

    if (real != NODATA) {
	if (imag != NODATA) {
	    for (k = 0; k < cplx->length; k++) {
		rx = exp(real->data[k]);
		cplx->real->data[k] = rx * cos(imag->data[k]);
		cplx->imag->data[k] = rx * sin(imag->data[k]);
	    }
	} else {
	    for (k = 0; k < cplx->length; k++) {
		cplx->real->data[k] = exp(real->data[k]);
		cplx->imag->data[k] = 0.0;
	    }
	}
    } else {
	if (imag != NODATA) {
	    for (k = 0; k < cplx->length; k++) {
		cplx->real->data[k] = cos(imag->data[k]);
		cplx->imag->data[k] = sin(imag->data[k]);
	    }
	} else {
	    for (k = 0; k < cplx->length; k++) {
		cplx->real->data[k] = 1.0;
		cplx->imag->data[k] = 0.0;
	    }
	}
    }

    return cplx;
}

void dcexp(DCOMPLEX cplx)
{
    long k;
    double a;

    for (k = 0; k < cplx->length; k++) {
	a = exp(cplx->real->data[k]);
	cplx->real->data[k] = a * cos(cplx->imag->data[k]);
	cplx->imag->data[k] = a * sin(cplx->imag->data[k]);
    }

    return;
}

DCOMPLEX xdcexp(DCOMPLEX x)
{
    DCOMPLEX y;

    y = xdcclone(x);
    dcexp(y);

    return y;
}
