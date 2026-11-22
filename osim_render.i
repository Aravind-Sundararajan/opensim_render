%module osim_render

%{
#include "mesh_loader.h"
%}

// Standard library support
%include <std_string.i>
%include <std_vector.i>
%include <std_shared_ptr.i>

// Declare shared pointer support for MeshData
%shared_ptr(osim_render::MeshData)

// String handling
%apply std::string { std::string& }

// Vector templates for Python
namespace std {
    %template(FloatVector) vector<float>;
    %template(IntVector) vector<int>;
}

// Exception handling - convert C++ exceptions to Python
%exception {
    try {
        $action
    } catch (const std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return NULL;
    } catch (...) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown error in C++ code");
        return NULL;
    }
}

// Custom typemap for float bounds[6] array
%typemap(out) float bounds[6] {
    $result = PyList_New(6);
    for (int i = 0; i < 6; i++) {
        PyList_SetItem($result, i, PyFloat_FromDouble((double)$1[i]));
    }
}

%typemap(in) float bounds[6] {
    if (!PyList_Check($input) || PyList_Size($input) != 6) {
        PyErr_SetString(PyExc_TypeError, "Expected a list of 6 floats");
        return NULL;
    }

    for (int i = 0; i < 6; i++) {
        PyObject* item = PyList_GetItem($input, i);
        if (!PyFloat_Check(item) && !PyLong_Check(item)) {
            PyErr_SetString(PyExc_TypeError, "List items must be floats");
            return NULL;
        }
        $1[i] = static_cast<float>(PyFloat_AsDouble(item));
    }
}

// Include the C++ header file with all declarations
%include "mesh_loader.h"

// Director for allowing Python overrides (optional - for future extensibility)
// %feature("director") osim_render::MeshLoader;
