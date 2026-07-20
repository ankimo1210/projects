#pragma once
// Minimal CSV output. Cells never contain commas/quotes in this project,
// so no quoting/escaping is implemented.
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace lab {

template <class T>
std::string cell(const T& v) {
    std::ostringstream os;
    os.precision(8);
    os << v;
    return os.str();
}

class CsvWriter {
public:
    CsvWriter(const std::filesystem::path& file, const std::vector<std::string>& header) {
        if (file.has_parent_path()) std::filesystem::create_directories(file.parent_path());
        out_.open(file);
        if (!out_) throw std::runtime_error("CsvWriter: cannot open " + file.string());
        write_row(header);
    }

    void write_row(const std::vector<std::string>& cells) {
        for (std::size_t i = 0; i < cells.size(); ++i) {
            if (i) out_ << ',';
            out_ << cells[i];
        }
        out_ << '\n';
    }

private:
    std::ofstream out_;
};

}  // namespace lab
