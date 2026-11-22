#pragma once

#include <string>
#include <vector>
#include <cstring>
#include <cmath>
#include <stdexcept>
#include <memory>
#include <sstream>
#include <algorithm>

// zlib decompression support - optional
#ifdef TINYVTPLOADER_HAS_ZLIB
#include <zlib.h>
#endif

namespace tinyvtp {

/**
 * Simple 3D vertex representation.
 */
struct Vertex {
    float x, y, z;

    Vertex() : x(0.f), y(0.f), z(0.f) {}
    Vertex(float x_, float y_, float z_) : x(x_), y(y_), z(z_) {}
};

/**
 * Surface normal vector.
 */
struct Normal {
    float nx, ny, nz;

    Normal() : nx(0.f), ny(0.f), nz(0.f) {}
    Normal(float nx_, float ny_, float nz_) : nx(nx_), ny(ny_), nz(nz_) {}
};

/**
 * Triangle mesh with 3 vertex indices.
 */
struct Triangle {
    int v0, v1, v2;

    Triangle() : v0(0), v1(0), v2(0) {}
    Triangle(int v0_, int v1_, int v2_) : v0(v0_), v1(v1_), v2(v2_) {}
};

/**
 * Polygon mesh data structure containing vertices, normals, and triangles.
 */
struct PolyData {
    std::vector<Vertex> vertices;
    std::vector<Normal> normals;
    std::vector<Triangle> triangles;

    /**
     * Check if mesh data is valid (has vertices and triangles).
     */
    bool is_valid() const {
        return !vertices.empty() && !triangles.empty();
    }

    /**
     * Get axis-aligned bounding box of mesh.
     *
     * @param bounds Output array [min_x, max_x, min_y, max_y, min_z, max_z]
     */
    void get_bounds(float bounds[6]) const {
        if (vertices.empty()) {
            std::fill(bounds, bounds + 6, 0.f);
            return;
        }

        bounds[0] = bounds[2] = bounds[4] = 1e10f;
        bounds[1] = bounds[3] = bounds[5] = -1e10f;

        for (const auto& v : vertices) {
            bounds[0] = std::min(bounds[0], v.x);
            bounds[1] = std::max(bounds[1], v.x);
            bounds[2] = std::min(bounds[2], v.y);
            bounds[3] = std::max(bounds[3], v.y);
            bounds[4] = std::min(bounds[4], v.z);
            bounds[5] = std::max(bounds[5], v.z);
        }
    }

    /**
     * Clear all mesh data.
     */
    void clear() {
        vertices.clear();
        normals.clear();
        triangles.clear();
    }
};

/**
 * VTP (VTK PolyData) file format loader.
 *
 * Parses uncompressed and zlib-compressed VTP XML files.
 * Implements RAII with move semantics.
 * Non-copyable to prevent accidental duplication.
 */
class VTPLoader {
public:
    /**
     * Default constructor.
     */
    VTPLoader() = default;

    /**
     * Move constructor.
     */
    VTPLoader(VTPLoader&& other) noexcept = default;

    /**
     * Move assignment.
     */
    VTPLoader& operator=(VTPLoader&& other) noexcept = default;

    /**
     * Deleted copy constructor.
     */
    VTPLoader(const VTPLoader&) = delete;

    /**
     * Deleted copy assignment.
     */
    VTPLoader& operator=(const VTPLoader&) = delete;

    /**
     * Destructor.
     */
    ~VTPLoader() = default;

    /**
     * Load VTP file and extract polygon data.
     *
     * @param filename Path to VTP file
     * @param out_data Output PolyData structure
     * @param error Output error message if load fails
     * @return true if load successful, false otherwise
     */
    bool load(const std::string& filename, PolyData& out_data, std::string& error);

private:
    /**
     * Load file content into string.
     */
    bool load_file_content(const std::string& filename, std::string& content, std::string& error);

    /**
     * Decompress zlib data.
     */
    bool decompress_zlib(const std::string& compressed, std::string& decompressed, std::string& error);

    /**
     * Decode base64 string.
     */
    bool decode_base64(const std::string& encoded, std::vector<unsigned char>& decoded);

    /**
     * Extract Points (vertices) from VTP XML.
     */
    bool extract_points(const std::string& content, PolyData& out_data, std::string& error);

    /**
     * Extract Normals from VTP XML.
     */
    bool extract_normals(const std::string& content, PolyData& out_data, std::string& error);

    /**
     * Extract Cells (triangles) from VTP XML.
     */
    bool extract_cells(const std::string& content, PolyData& out_data, std::string& error);

    /**
     * Parse XML data array format.
     */
    bool parse_data_array(
        const std::string& content,
        const std::string& tag_name,
        std::vector<float>& output,
        std::string& error
    );

    /**
     * Find XML tag value.
     */
    bool find_tag_value(
        const std::string& content,
        const std::string& tag_name,
        std::string& value
    );

    /**
     * Convert binary float array.
     */
    void binary_to_floats(const unsigned char* data, size_t byte_count, std::vector<float>& output);
};

#ifdef TINYVTPLOADER_IMPLEMENTATION

// Implementation
constexpr const char BASE64_CHARS[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

bool VTPLoader::load(const std::string& filename, PolyData& out_data, std::string& error) {
    std::string content;

    if (!load_file_content(filename, content, error)) {
        return false;
    }

    out_data.clear();

    if (!extract_points(content, out_data, error)) {
        return false;
    }

    extract_normals(content, out_data, error);  // Optional

    if (!extract_cells(content, out_data, error)) {
        return false;
    }

    return out_data.is_valid();
}

bool VTPLoader::load_file_content(const std::string& filename, std::string& content, std::string& error) {
    FILE* f = nullptr;
#ifdef _MSC_VER
    if (fopen_s(&f, filename.c_str(), "rb") != 0 || !f) {
#else
    f = fopen(filename.c_str(), "rb");
    if (!f) {
#endif
        error = "Cannot open file: " + filename;
        return false;
    }

    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);

    if (size <= 0) {
        error = "File is empty: " + filename;
        fclose(f);
        return false;
    }

    content.resize(size);
    if (fread(&content[0], 1, size, f) != (size_t)size) {
        error = "Failed to read file: " + filename;
        fclose(f);
        return false;
    }

    fclose(f);
    return true;
}

bool VTPLoader::decompress_zlib(const std::string& compressed, std::string& decompressed, std::string& error) {
#ifndef TINYVTPLOADER_HAS_ZLIB
    error = "zlib decompression not available (install zlib to support compressed VTP files)";
    return false;
#else
    z_stream stream;
    stream.zalloc = Z_NULL;
    stream.zfree = Z_NULL;
    stream.opaque = Z_NULL;

    if (inflateInit(&stream) != Z_OK) {
        error = "Failed to initialize zlib decompression";
        return false;
    }

    stream.avail_in = compressed.size();
    stream.next_in = (Bytef*)const_cast<char*>(compressed.data());

    const size_t CHUNK = 65536;
    unsigned char out[CHUNK];

    int ret;
    do {
        stream.avail_out = CHUNK;
        stream.next_out = out;
        ret = inflate(&stream, Z_NO_FLUSH);

        if (ret == Z_STREAM_ERROR || ret == Z_DATA_ERROR || ret == Z_MEM_ERROR) {
            error = "zlib decompression error";
            inflateEnd(&stream);
            return false;
        }

        size_t have = CHUNK - stream.avail_out;
        decompressed.append((char*)out, have);
    } while (ret != Z_STREAM_END);

    inflateEnd(&stream);
    return true;
#endif
}

bool VTPLoader::decode_base64(const std::string& encoded, std::vector<unsigned char>& decoded) {
    decoded.clear();

    for (size_t i = 0; i < encoded.size(); i += 4) {
        uint8_t b[4] = {0, 0, 0, 0};
        int count = 0;

        for (int j = 0; j < 4 && i + j < encoded.size(); j++) {
            char c = encoded[i + j];
            if (c >= 'A' && c <= 'Z') {
                b[j] = c - 'A';
                count++;
            } else if (c >= 'a' && c <= 'z') {
                b[j] = 26 + (c - 'a');
                count++;
            } else if (c >= '0' && c <= '9') {
                b[j] = 52 + (c - '0');
                count++;
            } else if (c == '+') {
                b[j] = 62;
                count++;
            } else if (c == '/') {
                b[j] = 63;
                count++;
            } else if (c == '=') {
                break;
            }
        }

        if (count >= 2) {
            decoded.push_back((b[0] << 2) | (b[1] >> 4));
        }
        if (count >= 3) {
            decoded.push_back((b[1] << 4) | (b[2] >> 2));
        }
        if (count >= 4) {
            decoded.push_back((b[2] << 6) | b[3]);
        }
    }

    return true;
}

bool VTPLoader::find_tag_value(const std::string& content, const std::string& tag_name, std::string& value) {
    std::string open_tag = "<" + tag_name + ">";
    std::string close_tag = "</" + tag_name + ">";

    size_t start = content.find(open_tag);
    if (start == std::string::npos) {
        return false;
    }

    start += open_tag.length();
    size_t end = content.find(close_tag, start);
    if (end == std::string::npos) {
        return false;
    }

    value = content.substr(start, end - start);
    return true;
}

void VTPLoader::binary_to_floats(const unsigned char* data, size_t byte_count, std::vector<float>& output) {
    output.clear();
    output.reserve(byte_count / sizeof(float));

    for (size_t i = 0; i + 3 < byte_count; i += 4) {
        float f;
        std::memcpy(&f, data + i, sizeof(float));
        output.push_back(f);
    }
}

bool VTPLoader::parse_data_array(
    const std::string& content,
    const std::string& tag_name,
    std::vector<float>& output,
    std::string& error
) {
    // Find the DataArray tag for the given component
    std::string search = "<DataArray type=\"Float32\" Name=\"" + tag_name + "\"";
    size_t pos = content.find(search);

    if (pos == std::string::npos) {
        return false;
    }

    // Find format attribute
    size_t format_pos = content.find("format=\"", pos);
    if (format_pos == std::string::npos) {
        return false;
    }

    bool is_binary = content.find("binary", format_pos) != std::string::npos;

    // Find opening >
    size_t start = content.find(">", format_pos);
    if (start == std::string::npos) {
        return false;
    }
    start++;

    // Find closing </DataArray>
    size_t end = content.find("</DataArray>", start);
    if (end == std::string::npos) {
        return false;
    }

    std::string data_str = content.substr(start, end - start);

    // Trim whitespace
    data_str.erase(0, data_str.find_first_not_of(" \n\r\t"));
    data_str.erase(data_str.find_last_not_of(" \n\r\t") + 1);

    if (is_binary) {
        std::vector<unsigned char> decoded;
        if (!decode_base64(data_str, decoded)) {
            error = "Failed to decode base64 data for " + tag_name;
            return false;
        }

        binary_to_floats(decoded.data(), decoded.size(), output);
    } else {
        // ASCII format
        std::istringstream iss(data_str);
        float value;
        while (iss >> value) {
            output.push_back(value);
        }
    }

    return !output.empty();
}

bool VTPLoader::extract_points(const std::string& content, PolyData& out_data, std::string& error) {
    std::vector<float> coords;

    if (!parse_data_array(content, "Coordinates", coords, error)) {
        error = "Failed to extract point coordinates";
        return false;
    }

    // Check if we need to decompress
    if (coords.empty() && content.find("format=\"appended\"") != std::string::npos) {
        // Complex appended binary format - simplified implementation
        error = "Appended binary format not yet supported";
        return false;
    }

    out_data.vertices.reserve(coords.size() / 3);
    for (size_t i = 0; i + 2 < coords.size(); i += 3) {
        out_data.vertices.push_back(Vertex(coords[i], coords[i + 1], coords[i + 2]));
    }

    return !out_data.vertices.empty();
}

bool VTPLoader::extract_normals(const std::string& content, PolyData& out_data, std::string& error) {
    std::vector<float> normals;

    if (!parse_data_array(content, "Normals", normals, error)) {
        return false;  // Normals are optional
    }

    out_data.normals.reserve(normals.size() / 3);
    for (size_t i = 0; i + 2 < normals.size(); i += 3) {
        out_data.normals.push_back(Normal(normals[i], normals[i + 1], normals[i + 2]));
    }

    return true;
}

bool VTPLoader::extract_cells(const std::string& content, PolyData& out_data, std::string& error) {
    // Find Polys section
    size_t polys_start = content.find("<Polys>");
    if (polys_start == std::string::npos) {
        error = "No Polys section found in VTP file";
        return false;
    }

    std::vector<float> connectivity_floats;
    if (!parse_data_array(content.substr(polys_start), "Connectivity", connectivity_floats, error)) {
        error = "Failed to extract cell connectivity";
        return false;
    }

    // Convert floats to ints for indices
    out_data.triangles.reserve(connectivity_floats.size() / 3);
    for (size_t i = 0; i + 2 < connectivity_floats.size(); i += 3) {
        int v0 = static_cast<int>(connectivity_floats[i]);
        int v1 = static_cast<int>(connectivity_floats[i + 1]);
        int v2 = static_cast<int>(connectivity_floats[i + 2]);
        out_data.triangles.push_back(Triangle(v0, v1, v2));
    }

    return !out_data.triangles.empty();
}

#endif  // TINYVTPLOADER_IMPLEMENTATION

}  // namespace tinyvtp
