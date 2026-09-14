#include <ignition/common/Mesh.hh>
#include <ignition/common/MeshManager.hh>
#include <ignition/common/SubMesh.hh>
#include <cmath>
#include <filesystem>
#include <iostream>

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  unsigned files = 0, submeshes = 0;
  auto *manager = ignition::common::MeshManager::Instance();
  for (const auto &entry : std::filesystem::directory_iterator(argv[1])) {
    if (entry.path().extension() != ".obj") continue;
    const auto *mesh = manager->Load(entry.path().string());
    if (!mesh || !mesh->SubMeshCount()) return 3;
    for (unsigned i = 0; i < mesh->SubMeshCount(); ++i) {
      auto part = mesh->SubMeshByIndex(i).lock();
      if (!part || !part->VertexCount() || part->VertexCount() != part->NormalCount()) {
        std::cerr << entry.path() << " missing submesh normals\n"; return 4;
      }
      for (unsigned n = 0; n < part->NormalCount(); ++n) {
        double length = part->Normal(n).Length();
        if (!std::isfinite(length) || std::abs(length - 1.) > 1e-5) return 5;
      }
      ++submeshes;
    }
    std::cout << entry.path().filename() << " vertices=" << mesh->VertexCount()
              << " normals=" << mesh->NormalCount() << " PASS\n";
    ++files;
  }
  std::cout << "checked_files=" << files << " submeshes=" << submeshes << '\n';
  return files ? 0 : 6;
}
