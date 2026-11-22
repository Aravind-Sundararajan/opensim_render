#include "mesh_loader.h"
#include "tiny_vtp_loader.h"
#include "tiny_obj_loader.h"

#include <cmath>
#include <algorithm>
#include <cctype>

namespace osim_render {

bool MeshData::is_valid() const {
    return !vertices.empty() && !indices.empty();
}

void MeshData::get_bounds(float bounds[6]) const {
    if (vertices.empty()) {
        std::fill(bounds, bounds + 6, 0.f);
        return;
    }

    bounds[0] = bounds[2] = bounds[4] = 1e10f;
    bounds[1] = bounds[3] = bounds[5] = -1e10f;

    for (size_t i = 0; i < vertices.size(); i += 3) {
        bounds[0] = std::min(bounds[0], vertices[i]);
        bounds[1] = std::max(bounds[1], vertices[i]);
        bounds[2] = std::min(bounds[2], vertices[i + 1]);
        bounds[3] = std::max(bounds[3], vertices[i + 1]);
        bounds[4] = std::min(bounds[4], vertices[i + 2]);
        bounds[5] = std::max(bounds[5], vertices[i + 2]);
    }
}

int MeshData::vertex_count() const {
    return static_cast<int>(vertices.size() / 3);
}

int MeshData::triangle_count() const {
    return static_cast<int>(indices.size() / 3);
}

/**
 * Implementation details (Pimpl pattern).
 */
class MeshLoader::Impl {
public:
    std::string error;
};

MeshLoader::MeshLoader() : impl_(std::make_unique<Impl>()) {
}

MeshLoader::~MeshLoader() = default;

std::string MeshLoader::detect_format(const std::string& filename) const {
    if (filename.length() < 4) {
        return "unknown";
    }

    std::string ext = filename.substr(filename.length() - 4);

    // Convert to lowercase
    for (char& c : ext) {
        c = std::tolower(static_cast<unsigned char>(c));
    }

    if (ext == ".obj") {
        return "obj";
    } else if (ext == ".vtp") {
        return "vtp";
    }

    return "unknown";
}

std::shared_ptr<MeshData> MeshLoader::load(const std::string& filename) {
    std::string format = detect_format(filename);

    if (format == "obj") {
        return load_obj(filename);
    } else if (format == "vtp") {
        return load_vtp(filename);
    } else {
        impl_->error = "Unknown file format: " + filename;
        return nullptr;
    }
}

std::shared_ptr<MeshData> MeshLoader::load_obj(const std::string& filename) {
    tinyobj::attrib_t attrib;
    std::vector<tinyobj::shape_t> shapes;
    std::vector<tinyobj::material_t> materials;
    std::string err;
    std::string warn;

    bool success = tinyobj::LoadObj(
        &attrib,
        &shapes,
        &materials,
        &warn,
        &err,
        filename.c_str()
    );

    if (!warn.empty()) {
        impl_->error = "OBJ load warning: " + warn;
    }

    if (!success) {
        impl_->error = "Failed to load OBJ file: " + filename;
        if (!err.empty()) {
            impl_->error += " (" + err + ")";
        }
        return nullptr;
    }

    auto mesh = std::make_shared<MeshData>();

    // Collect all vertices
    for (const auto& shape : shapes) {
        for (const auto& index : shape.mesh.indices) {
            // Vertex position
            mesh->vertices.push_back(attrib.vertices[3 * size_t(index.vertex_index) + 0]);
            mesh->vertices.push_back(attrib.vertices[3 * size_t(index.vertex_index) + 1]);
            mesh->vertices.push_back(attrib.vertices[3 * size_t(index.vertex_index) + 2]);

            // Vertex normal
            if (index.normal_index >= 0) {
                mesh->normals.push_back(attrib.normals[3 * size_t(index.normal_index) + 0]);
                mesh->normals.push_back(attrib.normals[3 * size_t(index.normal_index) + 1]);
                mesh->normals.push_back(attrib.normals[3 * size_t(index.normal_index) + 2]);
            }

            mesh->indices.push_back(static_cast<int>(mesh->vertices.size() / 3 - 1));
        }
    }

    // If no normals were provided, compute them
    if (mesh->normals.empty() && !mesh->vertices.empty()) {
        mesh->normals.resize(mesh->vertices.size(), 0.f);

        for (size_t i = 0; i < mesh->indices.size(); i += 3) {
            int v0 = mesh->indices[i];
            int v1 = mesh->indices[i + 1];
            int v2 = mesh->indices[i + 2];

            // Get vertex positions
            float v0x = mesh->vertices[3 * v0], v0y = mesh->vertices[3 * v0 + 1], v0z = mesh->vertices[3 * v0 + 2];
            float v1x = mesh->vertices[3 * v1], v1y = mesh->vertices[3 * v1 + 1], v1z = mesh->vertices[3 * v1 + 2];
            float v2x = mesh->vertices[3 * v2], v2y = mesh->vertices[3 * v2 + 1], v2z = mesh->vertices[3 * v2 + 2];

            // Compute edges
            float e1x = v1x - v0x, e1y = v1y - v0y, e1z = v1z - v0z;
            float e2x = v2x - v0x, e2y = v2y - v0y, e2z = v2z - v0z;

            // Compute cross product (face normal)
            float nx = e1y * e2z - e1z * e2y;
            float ny = e1z * e2x - e1x * e2z;
            float nz = e1x * e2y - e1y * e2x;

            // Normalize
            float len = std::sqrt(nx * nx + ny * ny + nz * nz);
            if (len > 1e-6f) {
                nx /= len;
                ny /= len;
                nz /= len;
            }

            // Add to vertex normals
            mesh->normals[3 * v0] += nx;
            mesh->normals[3 * v0 + 1] += ny;
            mesh->normals[3 * v0 + 2] += nz;

            mesh->normals[3 * v1] += nx;
            mesh->normals[3 * v1 + 1] += ny;
            mesh->normals[3 * v1 + 2] += nz;

            mesh->normals[3 * v2] += nx;
            mesh->normals[3 * v2 + 1] += ny;
            mesh->normals[3 * v2 + 2] += nz;
        }

        // Normalize vertex normals
        for (size_t i = 0; i < mesh->normals.size(); i += 3) {
            float nx = mesh->normals[i];
            float ny = mesh->normals[i + 1];
            float nz = mesh->normals[i + 2];

            float len = std::sqrt(nx * nx + ny * ny + nz * nz);
            if (len > 1e-6f) {
                mesh->normals[i] /= len;
                mesh->normals[i + 1] /= len;
                mesh->normals[i + 2] /= len;
            }
        }
    }

    if (!mesh->is_valid()) {
        impl_->error = "OBJ file produced invalid mesh: " + filename;
        return nullptr;
    }

    return mesh;
}

std::shared_ptr<MeshData> MeshLoader::load_vtp(const std::string& filename) {
    tinyvtp::VTPLoader loader;
    tinyvtp::PolyData poly_data;
    std::string error;

    if (!loader.load(filename, poly_data, error)) {
        impl_->error = "Failed to load VTP file: " + error;
        return nullptr;
    }

    auto mesh = std::make_shared<MeshData>();

    // Convert vertices to flattened array
    mesh->vertices.reserve(poly_data.vertices.size() * 3);
    for (const auto& v : poly_data.vertices) {
        mesh->vertices.push_back(v.x);
        mesh->vertices.push_back(v.y);
        mesh->vertices.push_back(v.z);
    }

    // Convert normals to flattened array
    mesh->normals.reserve(poly_data.normals.size() * 3);
    for (const auto& n : poly_data.normals) {
        mesh->normals.push_back(n.nx);
        mesh->normals.push_back(n.ny);
        mesh->normals.push_back(n.nz);
    }

    // Convert triangles to indices
    mesh->indices.reserve(poly_data.triangles.size() * 3);
    for (const auto& t : poly_data.triangles) {
        mesh->indices.push_back(t.v0);
        mesh->indices.push_back(t.v1);
        mesh->indices.push_back(t.v2);
    }

    if (!mesh->is_valid()) {
        impl_->error = "VTP file produced invalid mesh: " + filename;
        return nullptr;
    }

    return mesh;
}

std::string MeshLoader::get_error() const {
    return impl_->error;
}

}  // namespace osim_render
