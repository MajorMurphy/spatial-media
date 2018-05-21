#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2017 Vimeo. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MPEG sv3d mesh processing classes.

Enables the injection of an sv3d mesh project box The mesh projection box specification
conforms to that outlined in docs/spherical-video-v2-rfc.md
"""

import struct
import math
import io

from spatialmedia.mpeg import box
from spatialmedia.mpeg import constants
from spatialmedia.mpeg import bitwiseio


def load(fh, position=None, end=None):
    """ Loads the mesh projection box located at position in an mp4 file. Assuming raw encoding

    Args:
      fh: file handle, input file handle.
      position: int or None, current file position.

    Returns:
      new_box: box, mesh box box loaded from the file location or None.
    """
    if position is None:
        position = fh.tell()

    fh.seek(position)
    new_box = meshBox()
    new_box.position = position
    new_box.content_size = struct.unpack(">I", fh.read(4))[0]
    name = fh.read(4).decode('latin1')

    if (name != 'mesh'):
        print ("Error: box is not an mesh box.")
        return None

    print end
    print fh.tell()
    print new_box.content_size

    if (position + new_box.content_size > end):
        print ("Error: mesh box size exceeds bounds.")
        return None

    """ mesh box is 4 byte size (include size itself)
        id 'mesh'
        1 bit reserved
        31 bit co-ord count
        co-ordinates, 32bit float x co-ord count
        1 bit reserved
        31 bit vertex count
        vertex count x 5 (x,y,z,u,v) x ceil(log2(coordinate_count * 2)) encoded index to co-ords
        0-7 bits padding to get to byte boundary
        1 bit reserved
        31 bit vertex list count
        vertex list count x (
            1 byte texture_id,
            1 byte index_type (triangles, tri-strip or tri-fan)
            1 bit reserved
            31 bit index count
            index count x ceil(log2(coordinate_count * 2)) encoded index )
    """
    


    new_box.coordinate_count = struct.unpack(">I", fh.read(4))[0]
    
    new_box.coordinates = struct.unpack(">{0}f".format(new_box.coordinate_count), fh.read(4*new_box.coordinate_count))
    
    print new_box.coordinates

    ccsb =  int(math.ceil(math.log(new_box.coordinate_count * 2, 2.0)))

    new_box.vertex_count = struct.unpack(">I", fh.read(4))[0]

    print "coordinate_count:{0}".format(new_box.coordinate_count);
    print "vertex_count:{0}".format(new_box.vertex_count);
    print "ccsb:{0}".format(ccsb);

    """
       vertex_buffer = fh.read(5*ccsb*new_box.vertex_count);
    """

    bit_read = bitwiseio.BitReader(fh)

    new_box.vertex_buffer = []

    """ read in bits, ccsb bits at a time """
    for vertex_loop in range(new_box.vertex_count):
        tmp = {'x': bit_read.readbits(ccsb), 'y':bit_read.readbits(ccsb),'z':bit_read.readbits(ccsb), 'u':bit_read.readbits(ccsb), 'v':bit_read.readbits(ccsb) }
        print tmp
        new_box.vertex_buffer.append ( tmp )

    new_box.vertex_list_count = struct.unpack(">I", fh.read(4))[0]
    ccsb =  int(math.ceil(math.log(new_box.vertex_count * 2, 2.0)))


    print "vertex_list_count:{0}".format(new_box.vertex_list_count);
    print "ccsb:{0}".format(ccsb);

    new_box.vertex_list = []
    bit_read2 = bitwiseio.BitReader(fh)


    for x in range(new_box.vertex_list_count):
        texture_id = fh.read(1)
        index_type = fh.read(1)
        index_count = struct.unpack(">I", fh.read(4))[0]
        index_as_delta = []
        for y in range(index_count):
            index_as_delta.append(bit_read2.readbits(ccsb))
        tmp = {'txt':texture_id, 'type':index_type, 'count':index_count, 'strip':index_as_delta}
        print tmp
        new_box.vertex_list.append (tmp)

    return new_box


def gen_flat_mesh(grid, z_dist, x_scale, y_scale):

    """
        Create a hemi-sphere.
        top and bottom are triangle fans joined at the pole
        Rest is a grid of triangle strips.
        
    """
    coordinates = []
    vertices = []
    triangles = []
    triangle_list = []
    
    point_count = grid+1;
    x_offset = x_scale / 2
    y_offset = y_scale / 2

    coord_index = 0
    delta = 1.0 / grid
    
    for y_index in range(0,point_count):
        
        for x_index in range(0,point_count):
            
            u = x_index * delta
            v = y_index * delta
            z = -z_dist
            x = (u * x_scale) - x_offset
            y = (v * y_scale) - y_offset
            coordinates.append (x)
            coordinates.append (y)
            coordinates.append (z)
            coordinates.append (u)
            coordinates.append (v)
            
            print "x {0}, y {1}, z {2}, u {3}, v{4}".format(x,y,z,u, v)
            
            
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
    
    
    """
        generate triangles / triangles are counter-clockwise
        """
    
    strip = []
    
    for row_index in range(0, grid):
        for col_index in range(0, point_count):
            i = col_index + (row_index * point_count)
            j = col_index + ((row_index + 1)* point_count)
            strip.extend([i, j])
        if row_index < grid -1:
            print "degen"
            j = ((row_index + 1) * point_count)
            i = grid + ((row_index + 1) * point_count)
            strip.extend([i, j])

    triangles.append ({'txt': 0, 'type': 1, 'count': len(strip), 'list':strip})


    print triangles
    
    """
        encode the indices
    """
    return { 'coordinates':coordinates, 'vertices':vertices, 'triangles':triangles}


def gen_mesh(grid, radius, u_min, u_scale, v_min, v_scale):
    """
        Create a hemi-sphere.
        top and bottom are triangle fans joined at the pole
        Rest is a grid of triangle strips.
        
    """
    coordinates = []
    vertices = []
    triangles = []
    triangle_list = []
    
    point_count = grid+1;

    
    theta_delta = math.pi / grid
    phi_delta = math.pi / grid
    

    
    phi = -(math.pi/ 2.0)
    coord_index = 0

    for phi_index in range(0,point_count):

        theta = math.pi

        for theta_index in range(0,point_count):

            x = radius * math.cos(phi) * math.cos(theta)
            z = radius * math.cos(phi) * math.sin(theta)
            y = radius * math.sin(phi)
            coordinates.append (x)
            coordinates.append (y)
            coordinates.append (z)
            
            mag = math.sqrt((x*x)+(y*y)+(z*z));
            
            tmp = get_uv (x/mag,y/mag,z/mag, u_min, u_scale, v_min, v_scale)

            print "x {0}, y {1}, z {2}, u {3}, v{4}".format(x,y,z, tmp[0], tmp [1])
            
            coordinates.extend(tmp)
            
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1
            vertices.append(coord_index)
            coord_index += 1

            theta += theta_delta
        phi += phi_delta


    """
        generate triangles / triangles are counter-clockwise
    """
    
    strip = []

    for row_index in range(0, grid):
        for col_index in range(0, point_count):
            i = col_index + (row_index * point_count)
            j = col_index + ((row_index + 1)* point_count)
            strip.extend([i, j])
        if row_index < grid -1:
            print "degen"
            j = ((row_index + 1) * point_count)
            i = grid + ((row_index + 1) * point_count)
            strip.extend([i, j])

    triangles.append ({'txt': 0, 'type': 1, 'count': len(strip), 'list':strip})


    print triangles

    """
        encode the indices
    """
    return { 'coordinates':coordinates, 'vertices':vertices, 'triangles':triangles}

def get_uv(x,y,z, u_min, u_scale, v_min, v_scale):

    r = math.atan2(math.sqrt((x*x)+(y*y)),-z) / math.pi
    phi = math.atan2(y,x)

    # test lens correction
    #nr = (0.8*r) - (0.003 * r * r) + (0.03 * r * r * r) - (0.055 * r * r * r * r)

    u = r * math.cos(phi) + 0.5
    v = r * math.sin(phi) + 0.5
    


    return [(u *  u_scale) + u_min, (v * v_scale) + v_min]



class meshBox(box.Box):
    def __init__(self):
        box.Box.__init__(self)
        self.name = 'mesh'
        self.content_size = 0

    @staticmethod
    def create(metadata):
        new_box = meshBox()
        new_box.content_size = 0
        new_box.name = 'mesh'
        new_box.projection = metadata.spherical
        
        if metadata.stereo == 'none':
            new_box.contents = new_box.process_mesh(gen_mesh(39, 1, 0.0, 1, 0, 1))
        elif metadata.stereo == 'top-botton':
            new_box.contents = new_box.process_mesh(gen_mesh(39, 1, 0.0, 1, 0, 1)) + new_box.process_mesh(gen_mesh(39, 1, 0, 1, 0, 1))
        else:
            new_box.contents = new_box.process_mesh(gen_mesh(39, 1, 0.0, 1, 0, 1)) + new_box.process_mesh(gen_mesh(39, 1, 0, 1, 0, 1))
            # new_box.contents = new_box.process_mesh(gen_flat_mesh(39, 3 , 4.8, 2.7)) + new_box.process_mesh(gen_flat_mesh(39, 3 , 4.8, 2.7))

        return new_box

    def print_box(self, console):
        """ Prints the contents of this spherical (sv3d) box to the
            console.
        """
        console("\t\tMesh Projection:" )
        console("\t\t    [Mesh count]" % (len(self.meshes)))

    def get_metadata_string(self):
        """ Outputs a concise single line audio metadata string. """
        return "Mesh Projection: (%d)" % (len(self.meshes))
    
    def process_mesh(self, mesh_details):
        """ mesh box is 4 byte size (include size itself)
            id 'mesh'
            1 bit reserved
            31 bit co-ord count
            co-ordinates, 32bit float x co-ord count
            1 bit reserved
            31 bit vertex count
            vertex count x 5 (x,y,z,u,v) x ceil(log2(coordinate_count * 2)) encoded index to co-ords
            0-7 bits padding to get to byte boundary
            1 bit reserved
            31 bit vertex list count
            vertex list count x (
                1 byte texture_id,
                1 byte index_type (triangles, tri-strip or tri-fan)
                1 bit reserved
                31 bit index count
                index count x ceil(log2(coordinate_count * 2)) encoded index
                0-7 bits padding to get to byte boundary )
        """
        lfh = io.BytesIO('')
        
        coords = mesh_details['coordinates']
        num_coords = len(coords)
        
        lfh.write(self.name.encode('latin1'))
        lfh.write(struct.pack(">I", num_coords))
        lfh.write(struct.pack(">{0}f".format(num_coords), *coords))
        
        vertices = mesh_details['vertices']
        num_vertices = len(vertices) / 5;
        
        lfh.write(struct.pack(">I", num_vertices))
        
        bit_write = bitwiseio.BitWriter(lfh)
        ccsb =  int(math.ceil(math.log(num_coords * 2, 2.0)))

        previous_vertex = [0,0,0,0,0]

        count_previous = 0
        for vertex in vertices:
            delta = vertex - previous_vertex[count_previous]
            vertex_delta = 0
            if delta < 0:
                vertex_delta = (-delta * 2) + 1
            else:
                vertex_delta = delta * 2
            bit_write.writebits(vertex_delta, ccsb)
            previous_vertex[count_previous] = vertex
            count_previous += 1
            count_previous = count_previous % 5

        bit_write.flush()


        tri_lists = mesh_details['triangles']
        num_tri_lists = len(tri_lists)

        lfh.write(struct.pack(">I", num_tri_lists))

        ccsb =  int(math.ceil(math.log(num_vertices * 2, 2.0)))

        for strip in tri_lists:
            face_indices = strip['list']
            count = strip['count']
            lfh.write(struct.pack(">B", strip['txt']))
            lfh.write(struct.pack(">B", strip['type']))
            lfh.write(struct.pack(">I", strip['count']))
            previous_list_index = 0
            for list_index in strip['list']:
                delta = list_index - previous_list_index
                list_index_delta = 0
                if delta < 0:
                    list_index_delta = (-delta * 2) + 1
                else:
                    list_index_delta = delta * 2
                bit_write.writebits(list_index_delta, ccsb)
                previous_list_index = list_index
            bit_write.flush()

        lfh.flush()
        lfh.seek(0)
        mesh_bytes = lfh.read()
        return struct.pack(">I", len(mesh_bytes) + 4) + mesh_bytes


    def save(self, in_fh, out_fh, delta):
        
        """TODO:
        out_fh.write(struct.pack(">I", self.content_size + self.header_size))
        out_fh.write(self.name.encode('latin1'))
        """









