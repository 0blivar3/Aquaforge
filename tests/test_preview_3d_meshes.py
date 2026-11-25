import numpy as np

from app.preview_3d import _mesh_plane, _mesh_cube, _mesh_sphere, _mesh_cylinder


def _assert_valid_mesh(mesh):
    vertices, indices = mesh
    assert vertices.ndim == 2
    assert vertices.shape[1] == 11
    assert indices.ndim == 1
    assert indices.size % 3 == 0
    assert np.isfinite(vertices).all()
    assert indices.min() >= 0
    assert indices.max() < len(vertices)


def test_plane_mesh_is_valid():
    _assert_valid_mesh(_mesh_plane())


def test_cube_mesh_is_valid():
    _assert_valid_mesh(_mesh_cube())


def test_sphere_mesh_is_valid():
    _assert_valid_mesh(_mesh_sphere())


def test_cylinder_mesh_is_valid():
    _assert_valid_mesh(_mesh_cylinder())
