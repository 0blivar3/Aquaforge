#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace py = pybind11;
constexpr double PI = 3.14159265358979323846;

static uint64_t next_random(uint64_t& state) {
    state ^= state >> 12;
    state ^= state << 25;
    state ^= state >> 27;
    return state * 2685821657736338717ULL;
}
static double random_unit(uint64_t& state) {
    return static_cast<double>(next_random(state) >> 11) * (1.0 / 9007199254740992.0);
}

py::array_t<float> generate_heightmap(
    int width, int height, double wave_scale, double wave_strength,
    double frequency, double direction, double wind_strength,
    double ripple_intensity, double ripple_scale, int detail,
    double distortion, uint64_t seed) {
    if (width < 16 || width > 8192 || height < 16 || height > 8192)
        throw std::invalid_argument("Resolution must be between 16 and 8192 pixels");
    if (detail < 1 || detail > 12)
        throw std::invalid_argument("Detail must be between 1 and 12");

    py::array_t<float> output({height, width});
    auto* out = output.mutable_data();
    const double base_angle = direction * PI / 180.0;
    const int waves = std::max(2, detail + 1);
    uint64_t state = seed ? seed : 0x9E3779B97F4A7C15ULL;
    std::vector<double> phases(waves), amplitudes(waves);
    std::vector<int> kxs(waves), kys(waves);
    std::vector<double> angles(waves);
    for (int i = 0; i < waves; ++i) {
        const double angle = base_angle + i * (PI * (3.0 - std::sqrt(5.0)));
        const int magnitude = std::max(1, static_cast<int>(std::round(
            wave_scale * frequency * (1.0 + i * 0.22))));
        int kx = static_cast<int>(std::round(std::cos(angle) * magnitude));
        int ky = static_cast<int>(std::round(std::sin(angle) * magnitude));
        if (kx == 0 && ky == 0) kx = 1;
        kxs[i] = kx; kys[i] = ky; angles[i] = angle;
        phases[i] = random_unit(state) * 2.0 * PI;
        const double wind_bias = 1.0 + wind_strength *
            std::max(0.0, std::cos(angle - base_angle));
        amplitudes[i] = wave_strength * wind_bias / waves / (1.0 + i * 0.8);
    }
    struct Ripple { int x, y; double phase, amplitude; };
    std::vector<Ripple> ripples(std::max(1, detail));
    for (int i = 0; i < static_cast<int>(ripples.size()); ++i) {
        const double angle = random_unit(state) * 2.0 * PI;
        const int freq = std::max(2, static_cast<int>(std::round(ripple_scale * (1.0 + i * 0.12))));
        int kx = static_cast<int>(std::round(std::cos(angle) * freq));
        int ky = static_cast<int>(std::round(std::sin(angle) * freq));
        if (kx == 0) kx = 1;
        ripples[i] = {kx, ky, random_unit(state) * 2.0 * PI,
            ripple_intensity / (i + 1.0) / std::max(1, detail)};
    }
    const double distortion_phase = random_unit(state) * 2.0 * PI;
    double sum = 0.0;
    {
        py::gil_scoped_release release;
        for (int y = 0; y < height; ++y) {
            const double v = static_cast<double>(y) / height;
            for (int x = 0; x < width; ++x) {
                const double u = static_cast<double>(x) / width;
                double value = 0.0;
                for (int i = 0; i < waves; ++i)
                    value += amplitudes[i] * std::sin(2.0 * PI *
                        (kxs[i] * u + kys[i] * v) + phases[i]);
                for (const auto& r : ripples)
                    value += r.amplitude * std::sin(2.0 * PI *
                        (r.x * u + r.y * v) + r.phase);
                if (distortion != 0.0) {
                    const double modulation = std::sin(2.0 * PI * (2.0 * u + v) + distortion_phase);
                    value *= 1.0 + distortion * modulation;
                }
                out[y * width + x] = static_cast<float>(value);
                sum += value;
            }
        }
        const double mean = sum / (static_cast<double>(width) * height);
        double peak = 0.0;
        for (int i = 0; i < width * height; ++i) {
            out[i] = static_cast<float>(out[i] - mean);
            peak = std::max(peak, std::abs(static_cast<double>(out[i])));
        }
        if (peak > 1e-8)
            for (int i = 0; i < width * height; ++i)
                out[i] = static_cast<float>(out[i] / peak);
    }
    return output;
}

py::array_t<uint8_t> height_to_normal(
    py::array_t<float, py::array::c_style | py::array::forcecast> input,
    double strength, const std::string& convention, bool seamless) {
    if (strength < 0.0) throw std::invalid_argument("strength cannot be negative");
    if (convention != "OpenGL" && convention != "DirectX")
        throw std::invalid_argument("y_convention must be 'OpenGL' or 'DirectX'");
    auto info = input.request();
    if (info.ndim != 2 || info.shape[0] < 2 || info.shape[1] < 2)
        throw std::invalid_argument("height must be a 2D array at least 2x2");
    const ssize_t h = info.shape[0], w = info.shape[1];
    const auto* src = static_cast<const float*>(info.ptr);
    py::array_t<uint8_t> output({h, w, static_cast<ssize_t>(3)});
    auto* dst = output.mutable_data();
    {
        py::gil_scoped_release release;
        for (ssize_t y = 0; y < h; ++y) {
            const ssize_t ym = seamless ? (y + h - 1) % h : std::max<ssize_t>(0, y - 1);
            const ssize_t yp = seamless ? (y + 1) % h : std::min<ssize_t>(h - 1, y + 1);
            for (ssize_t x = 0; x < w; ++x) {
                const ssize_t xm = seamless ? (x + w - 1) % w : std::max<ssize_t>(0, x - 1);
                const ssize_t xp = seamless ? (x + 1) % w : std::min<ssize_t>(w - 1, x + 1);
                const double dx = (src[y*w+xp] - src[y*w+xm]) *
                    (seamless ? 0.5 : (x == 0 || x == w-1 ? 1.0 : 0.5));
                double dy = (src[yp*w+x] - src[ym*w+x]) *
                    (seamless ? 0.5 : (y == 0 || y == h-1 ? 1.0 : 0.5));
                double nx = -dx * strength;
                double ny = -dy * strength;
                if (convention == "DirectX") ny = -ny;
                const double inv = 1.0 / std::sqrt(nx*nx + ny*ny + 1.0);
                nx *= inv; ny *= inv;
                const double nz = inv;
                const ssize_t i = (y*w+x)*3;
                dst[i] = static_cast<uint8_t>(std::clamp(std::lround((nx*0.5+0.5)*255.0), 0L, 255L));
                dst[i+1] = static_cast<uint8_t>(std::clamp(std::lround((ny*0.5+0.5)*255.0), 0L, 255L));
                dst[i+2] = static_cast<uint8_t>(std::clamp(std::lround((nz*0.5+0.5)*255.0), 0L, 255L));
            }
        }
    }
    return output;
}

PYBIND11_MODULE(_aquaforge_native, m) {
    m.doc() = "AquaForge C++17 compute backend";
    m.def("generate_heightmap", &generate_heightmap);
    m.def("height_to_normal", &height_to_normal);
}
