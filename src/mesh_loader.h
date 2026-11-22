#pragma once

#include <memory>
#include <string>
#include <vector>

namespace osim_render {

/**
 * Mesh geometry data in flattened format suitable for VTK and rendering.
 *
 * Vertices and normals are stored as flattened arrays for efficient
 * data transfer to rendering engines.
 */
struct MeshData {
    /** Flattened vertices array [x0, y0, z0, x1, y1, z1, ...] */
    std::vector<float> vertices;

    /** Flattened normals array [nx0, ny0, nz0, nx1, ny1, nz1, ...] */
    std::vector<float> normals;

    /** Triangle indices [v0, v1, v2, v0, v1, v2, ...] */
    std::vector<int> indices;

    /**
     * Check if mesh data is valid (has vertices and indices).
     *
     * @return true if mesh has both vertices and indices
     */
    bool is_valid() const;

    /**
     * Get axis-aligned bounding box of mesh.
     *
     * @param bounds Output array [min_x, max_x, min_y, max_y, min_z, max_z]
     */
    void get_bounds(float bounds[6]) const;

    /**
     * Get vertex count.
     *
     * @return Number of vertices
     */
    int vertex_count() const;

    /**
     * Get triangle count.
     *
     * @return Number of triangles
     */
    int triangle_count() const;
};

/**
 * High-level mesh loader supporting OBJ and VTP formats.
 *
 * Uses Pimpl (Pointer to Implementation) idiom to hide implementation details.
 * Auto-detects format by file extension.
 * Returns shared pointers for automatic memory management.
 */
class MeshLoader {
public:
    /**
     * Construct a new MeshLoader.
     */
    MeshLoader();

    /**
     * Destructor.
     */
    ~MeshLoader();

    /**
     * Load a mesh from file (auto-detect format).
     *
     * @param filename Path to mesh file (.obj or .vtp)
     * @return Shared pointer to MeshData, nullptr on error
     */
    std::shared_ptr<MeshData> load(const std::string& filename);

    /**
     * Get last error message.
     *
     * @return Error message from last operation
     */
    std::string get_error() const;

private:
    /**
     * Load OBJ file format.
     *
     * @param filename Path to OBJ file
     * @return Shared pointer to MeshData, nullptr on error
     */
    std::shared_ptr<MeshData> load_obj(const std::string& filename);

    /**
     * Load VTP file format.
     *
     * @param filename Path to VTP file
     * @return Shared pointer to MeshData, nullptr on error
     */
    std::shared_ptr<MeshData> load_vtp(const std::string& filename);

    /**
     * Determine file format from extension.
     *
     * @param filename Path to file
     * @return Format string ("obj", "vtp", or "unknown")
     */
    std::string detect_format(const std::string& filename) const;

    /**
     * Pimpl - implementation details
     */
    class Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace osim_render
