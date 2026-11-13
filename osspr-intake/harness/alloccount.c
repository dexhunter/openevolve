#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

/* Counts PyObject allocator calls, including temporaries freed before return.
 * The hook is C so the counter itself does not allocate.
 */
static PyMemAllocatorEx orig;
static int installed = 0;
static volatile int enabled = 0;
static uint64_t count = 0;

static void *hook_malloc(void *ctx, size_t size) {
    (void)ctx;
    if (enabled) {
        count++;
    }
    return orig.malloc(orig.ctx, size);
}

static void *hook_calloc(void *ctx, size_t nelem, size_t elsize) {
    (void)ctx;
    if (enabled) {
        count++;
    }
    return orig.calloc(orig.ctx, nelem, elsize);
}

static void *hook_realloc(void *ctx, void *ptr, size_t new_size) {
    (void)ctx;
    if (enabled) {
        count++;
    }
    return orig.realloc(orig.ctx, ptr, new_size);
}

static void hook_free(void *ctx, void *ptr) {
    (void)ctx;
    orig.free(orig.ctx, ptr);
}

static PyObject *py_start(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    if (!installed) {
        PyMemAllocatorEx wrapped;
        PyMem_GetAllocator(PYMEM_DOMAIN_OBJ, &orig);
        wrapped.ctx = orig.ctx;
        wrapped.malloc = hook_malloc;
        wrapped.calloc = hook_calloc;
        wrapped.realloc = hook_realloc;
        wrapped.free = hook_free;
        PyMem_SetAllocator(PYMEM_DOMAIN_OBJ, &wrapped);
        installed = 1;
    }
    count = 0;
    enabled = 1;
    Py_RETURN_NONE;
}

static PyObject *py_stop(PyObject *self, PyObject *args) {
    (void)self;
    (void)args;
    enabled = 0;
    return PyLong_FromUnsignedLongLong(count);
}

static PyMethodDef methods[] = {
    {"start", py_start, METH_NOARGS, NULL},
    {"stop", py_stop, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT, "alloccount", NULL, -1, methods,
};

PyMODINIT_FUNC PyInit_alloccount(void) { return PyModule_Create(&moduledef); }
