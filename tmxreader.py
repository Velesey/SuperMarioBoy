#!/usr/bin/python
# -*- coding: utf-8 -*-

u"""
TileMap loader for python for Tiled, a generic tile map editor
from http://mapeditor.org/ .
It loads the \*.tmx files produced by Tiled.


"""

# Versioning scheme based on: http://en.wikipedia.org/wiki/Versioning#Designating_development_stage
#
#   +-- api change, probably incompatible with older versions
#   |     +-- enhancements but no api change
#   |     |
# major.minor[.build[.revision]]
#                |
#                +-|* 0 for alpha (status)
#                  |* 1 for beta (status)
#                  |* 2 for release candidate
#                  |* 3 for (public) release
#
# For instance:
#     * 1.2.0.1 instead of 1.2-a
#     * 1.2.1.2 instead of 1.2-b2 (beta with some bug fixes)
#     * 1.2.2.3 instead of 1.2-rc (release candidate)
#     * 1.2.3.0 instead of 1.2-r (commercial distribution)
#     * 1.2.3.5 instead of 1.2-r5 (commercial distribution with many bug fixes)

__revision__ = "$Rev: 114 $"
__version__ = "3.0.3." + __revision__[6:-2]
__author__ = u'DR0ID @ 2009-2011'

# import logging
# #the following few lines are needed to use logging if this module used without
# # a previous call to logging.basicConfig()
# if 0 == len(logging.root.handlers):
    # logging.basicConfig(level=logging.DEBUG)

# _LOGGER = logging.getLogger('tiledtmxloader')
# if __debug__:
    # _LOGGER.debug('%s loading ...' % (__name__))
#  -----------------------------------------------------------------------------


import sys
from xml.dom import minidom, Node
import StringIO
import os.path
import struct
import array

#  -----------------------------------------------------------------------------
class TileMap(object):
    u"""

    The TileMap holds all the map data.

    :Ivariables:
        orientation : string
            orthogonal or isometric or hexagonal or shifted
        tilewidth : int
            width of the tiles (for all layers)
        tileheight : int
            height of the tiles (for all layers)
        width : int
            width of the map (number of tiles)
        height : int
            height of the map (number of tiles)
        version : string
            version of the map format
        tile_sets : list
            list of TileSet
        properties : dict
            the propertis set in the editor, name-value pairs, strings
        pixel_width : int
            width of the map in pixels
        pixel_height : int
            height of the map in pixels
        layers : list
            list of TileLayer
        map_file_name : dict
            file name of the map
        named_layers : dict of string:TledLayer
            dict containing {name : TileLayer}
        named_tile_sets : dict
            dict containing {name : TileSet}

    """


    def __init__(self):
#        This is the top container for all data. The gid is the global id 
#       (for a image).
#        Before calling convert most of the values are strings. Some additional
#        values are also calculated, see convert() for details. After calling
#        convert, most values are integers or floats where appropriat.
        u"""
        The TileMap holds all the map data.
        """
        # set through parser
        self.orientation = None
        self.tileheight = 0
        self.tilewidth = 0
        self.width = 0
        self.height = 0
        self.version = 0
        self.tile_sets = [] # TileSet
        # ISSUE 9: object groups should be in the same order as layers
        self.layers = [] # WorldTileLayer <- what order? back to front (guessed)
        # self.object_groups = []
        self.properties = {} # {name: value}
        # additional info
        self.pixel_width = 0
        self.pixel_height = 0
        self.named_layers = {} # {name: layer}
        self.named_tile_sets = {} # {name: tile_set}
        self.map_file_name = ""

    def convert(self):
        u"""
        Converts numerical values from strings to numerical values.
        It also calculates or set additional data:
        pixel_width
        pixel_height
        named_layers
        named_tile_sets
        """
        self.tilewidth = int(self.tilewidth)
        self.tileheight = int(self.tileheight)
        self.width = int(self.width)
        self.height = int(self.height)
        self.pixel_width = self.width * self.tilewidth
        self.pixel_height = self.height * self.tileheight

        for layer in self.layers:
            # ISSUE 9
            if not layer.is_object_group:
                layer.tilewidth = self.tilewidth
                layer.tileheight = self.tileheight
                self.named_layers[layer.name] = layer
            layer.convert()

        for tile_set in self.tile_sets:
            self.named_tile_sets[tile_set.name] = tile_set
            tile_set.spacing = int(tile_set.spacing)
            tile_set.margin = int(tile_set.margin)
            for img in tile_set.images:
                if img.trans:
                    img.trans = (int(img.trans[:2], 16), \
                                 int(img.trans[2:4], 16), \
                                 int(img.trans[4:], 16))

    def decode(self):
        u"""
        Decodes the TileLayer encoded_content and saves it in decoded_content.
        """
        for layer in self.layers:
            if not layer.is_object_group:
                layer.decode()
#  -----------------------------------------------------------------------------


class TileSet(object):
    u"""
    A tileset holds the tiles and its images.

    :Ivariables:
        firstgid : int
            the first gid of this tileset
        name : string
            the name of this TileSet
        images : list
            list of TileImages
        tiles : list
            list of Tiles
        indexed_images : dict
            after calling load() it is dict containing id: image
        spacing : int
            the spacing between tiles
        marging : int
            the marging of the tiles
        properties : dict
            the propertis set in the editor, name-value pairs
        tilewidth : int
            the actual width of the tile, can be different from the tilewidth
            of the map
        tilehight : int
            the actual hight of th etile, can be different from the tilehight
            of the  map

    """

    def __init__(self):
        self.firstgid = 0
        self.name = None
        self.images = [] # TileImage
        self.tiles = [] # Tile
        self.indexed_images = {} # {id:image}
        self.spacing = 0
        self.margin = 0
        self.properties = {}
        self.tileheight = 0
        self.tilewidth = 0

#  -----------------------------------------------------------------------------

class TileImage(object):
    u"""
    An image of a tile or just an image.

    :Ivariables:
        id : int
            id of this image (has nothing to do with gid)
        format : string
            the format as string, only 'png' at the moment
        source : string
            filename of the image. either this is set or the content
        encoding : string
            encoding of the content
        trans : tuple of (r,g,b)
            the colorkey color, raw as hex, after calling convert just a 
            (r,g,b) tuple
        properties : dict
            the propertis set in the editor, name-value pairs
        image : TileImage
            after calling load the pygame surface
    """

    def __init__(self):
        self.id = 0
        self.format = None
        self.source = None
        self.encoding = None # from <data>...</data>
        self.content = None # from <data>...</data>
        self.image = None
        self.trans = None
        self.properties = {} # {name: value}

#  -----------------------------------------------------------------------------

class Tile(object):
    u"""
    A single tile.

    :Ivariables:
        id : int
            id of the tile gid = TileSet.firstgid + Tile.id
        images : list of :class:TileImage
            list of TileImage, either its 'id' or 'image data' will be set
        properties : dict of name:value
            the propertis set in the editor, name-value pairs
    """

# [20:22]	DR0ID_: to sum up: there are two use cases,
# if the tile element has a child element 'image' then tile is
# standalone with its own id and
# the other case where a tileset is present then it
# referes to the image with that id in the tileset

    def __init__(self):
        self.id = 0
        self.images = [] # uses TileImage but either only id will be set or image data
        self.properties = {} # {name: value}

#  -----------------------------------------------------------------------------

class TileLayer(object):
    u"""
    A layer of the world.

    :Ivariables:
        x : int
            position of layer in the world in number of tiles (not pixels)
        y : int
            position of layer in the world in number of tiles (not pixels)
        width : int
            number of tiles in x direction
        height : int
            number of tiles in y direction
        pixel_width : int
            width of layer in pixels
        pixel_height : int
            height of layer in pixels
        name : string
            name of this layer
        opacity : float
            float from 0 (full transparent) to 1.0 (opaque)
        decoded_content : list
            list of graphics id going through the map::

                e.g [1, 1, 1, ]
                where decoded_content[0]   is (0,0)
                      decoded_content[1]   is (1,0)
                      ...
                      decoded_content[w]   is (width,0)
                      decoded_content[w+1] is (0,1)
                      ...
                      decoded_content[w * h]  is (width,height)

                usage: graphics id = decoded_content[tile_x + tile_y * width]
        content2D : list
            list of list, usage: graphics id = content2D[x][y]

    """

    def __init__(self):
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.pixel_width = 0
        self.pixel_height = 0
        self.name = None
        self.opacity = -1
        self.encoding = None
        self.compression = None
        self.encoded_content = None
        self.decoded_content = []
        self.visible = True
        self.properties = {} # {name: value}
        self.content2D = None
        self.is_object_group = False    # ISSUE 9


    def decode(self):
        u"""
        Converts the contents in a list of integers which are the gid of the 
        used tiles. If necessairy it decodes and uncompresses the contents.
        """
        self.decoded_content = []
        if self.encoded_content:
            content = self.encoded_content
            if self.encoding:
                if self.encoding.lower() == u'base64':
                    content = decode_base64(content)
                elif self.encoding.lower() == u'csv':
                    list_of_lines = content.split()
                    for line in list_of_lines:
                        self.decoded_content.extend(line.split(','))
                    self.decoded_content = map(int, \
                                [val for val in self.decoded_content if val])
                    content = ""
                else:
                    raise Exception(u'unknown data encoding %s' % \
                                                                (self.encoding))
            else:
                # in the case of xml the encoded_content already contains a 
                # list of integers
                self.decoded_content = map(int, self.encoded_content)
                content = ""
            if self.compression:
                if self.compression == u'gzip':
                    content = decompress_gzip(content)
                elif self.compression == u'zlib':
                    content = decompress_zlib(content)
                else:
                    raise Exception(u'unknown data compression %s' % \
                                                            (self.compression))
        else:
            raise Exception(u'no encoded content to decode')

        struc = struct.Struct("<" + "I" * self.width)
        struc_unpack_from = struc.unpack_from
        self_decoded_content_extend = self.decoded_content.extend
        for idx in xrange(0, len(content), 4 * self.width):
            val = struc_unpack_from(content, idx)
            self_decoded_content_extend(val)

        arr = array.array('I')
        arr.fromlist(self.decoded_content)
        self.decoded_content = arr

        # TODO: generate property grid here??

        self._gen_2D()

    def _gen_2D(self):
        self.content2D = []

        # generate the needed lists and fill them
        for xpos in xrange(self.width):
            self.content2D.append(array.array('I'))
            for ypos in xrange(self.height):
                self.content2D[xpos].append( \
                                self.decoded_content[xpos + ypos * self.width])

    def pretty_print(self):
        num = 0
        for y in range(int(self.height)):
            output = u""
            for x in range(int(self.width)):
                output += str(self.decoded_content[num])
                num += 1
            print output

    def convert(self):
        self.opacity = float(self.opacity)
        self.x = int(self.x)
        self.y = int(self.y)
        self.width = int(self.width)
        self.height = int(self.height)
        self.pixel_width = self.width * self.tilewidth
        self.pixel_height = self.height * self.tileheight
        self.visible = bool(int(self.visible))

    # def get_visible_tile_range(self, xmin, ymin, xmax, ymax):
        # tile_w = self.pixel_width / self.width
        # tile_h = self.pixel_height / self.height
        # left = int(round(float(xmin) / tile_w)) - 1
        # right = int(round(float(xmax) / tile_w)) + 2
        # top = int(round(float(ymin) / tile_h)) - 1
        # bottom = int(round(float(ymax) / tile_h)) + 2
        # return (left, top, left - right, top - bottom)

    # def get_tiles(self, xmin, ymin, xmax, ymax):
        # tiles = []
        # if self.visible:
            # for ypos in range(ymin, ymax):
                # for xpos in range(xmin, xmax):
                    # try:
                        # img_idx = self.content2D[xpos][ypos]
                        # if img_idx:
                            # tiles.append((xpos, ypos, img_idx))
                    # except IndexError:
                        # pass
        # return tiles

#  -----------------------------------------------------------------------------


class MapObjectGroupLayer(object):
    u"""
    Group of objects on the map.

    :Ivariables:
        x : int
            the x position
        y : int
            the y position
        width : int
            width of the bounding box (usually 0, so no use)
        height : int
            height of the bounding box (usually 0, so no use)
        name : string
            name of the group
        objects : list
            list of the map objects

    """

    def __init__(self):
        self.width = 0
        self.height = 0
        self.name = None
        self.objects = []
        self.x = 0
        self.y = 0
        self.visible = True
        self.properties = {} # {name: value}
        self.is_object_group = True # ISSUE 9

    def convert(self):
        self.x = int(self.x)
        self.y = int(self.y)
        self.width = int(self.width)
        self.height = int(self.height)
        for map_obj in self.objects:
            map_obj.x = int(map_obj.x)
            map_obj.y = int(map_obj.y)
            map_obj.width = int(map_obj.width)
            map_obj.height = int(map_obj.height)

#  -----------------------------------------------------------------------------

class MapObject(object):
    u"""
    A single object on the map.

    :Ivariables:
        x : int
            x position relative to group x position
        y : int
            y position relative to group y position
        width : int
            width of this object
        height : int
            height of this object
        type : string
            the type of this object
        image_source : string
            source path of the image for this object
        image : :class:TileImage
            after loading this is the pygame surface containing the image
    """
    def __init__(self):
        self.name = None
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        self.type = None
        self.image_source = None
        self.image = None
        self.properties = {} # {name: value}

#  -----------------------------------------------------------------------------
def decode_base64(in_str):
    u"""
    Decodes a base64 string and returns it.

    :Parameters:
        in_str : string
            base64 encoded string

    :returns: decoded string
    """
    import base64
    return base64.decodestring(in_str)

#  -----------------------------------------------------------------------------
def decompress_gzip(in_str):
    u"""
    Uncompresses a gzip string and returns it.

    :Parameters:
        in_str : string
            gzip compressed string

    :returns: uncompressed string
    """
    import gzip
    # gzip can only handle file object therefore using StringIO
    copmressed_stream = StringIO.StringIO(in_str)
    gzipper = gzip.GzipFile(fileobj=copmressed_stream)
    content = gzipper.read()
    gzipper.close()
    return content

#  -----------------------------------------------------------------------------
def decompress_zlib(in_str):
    u"""
    Uncompresses a zlib string and returns it.

    :Parameters:
        in_str : string
            zlib compressed string

    :returns: uncompressed string
    """
    import zlib
    content = zlib.decompress(in_str)
    return content
#  -----------------------------------------------------------------------------
def printer(obj, ident=''):
    u"""
    Helper function, prints a hirarchy of objects.
    """
    import inspect
    print ident + obj.__class__.__name__.upper()
    ident += '    '
    lists = []
    for name in dir(obj):
        elem = getattr(obj, name)
        if isinstance(elem, list) and name != u'decoded_content':
            lists.append(elem)
        elif not inspect.ismethod(elem):
            if not name.startswith('__'):
                if name == u'data' and elem:
                    print ident + u'data = '
                    printer(elem, ident + '    ')
                else:
                    print ident + u'%s\t= %s' % (name, getattr(obj, name))
    for objt_list in lists:
        for _obj in objt_list:
            printer(_obj, ident + '    ')

#  -----------------------------------------------------------------------------

class VersionError(Exception): pass

#  -----------------------------------------------------------------------------
class TileMapParser(object):
    u"""
    Allows to parse and decode map files for 'Tiled', a open source map editor
    written in java. It can be found here: http://mapeditor.org/
    """

    def _build_tile_set(self, tile_set_node, world_map):
        tile_set = TileSet()
        self._set_attributes(tile_set_node, tile_set)
        if hasattr(tile_set, "source"):
            tile_set = self._parse_tsx(tile_set.source, tile_set, world_map)
        else:
            tile_set = self._get_tile_set(tile_set_node, tile_set, \
                                                            self.map_file_name)
        world_map.tile_sets.append(tile_set)

    def _parse_tsx(self, file_name, tile_set, world_map):
        # ISSUE 5: the *.tsx file is probably relative to the *.tmx file
        if not os.path.isabs(file_name):
            # print "map file name", self.map_file_name
            file_name = self._get_abs_path(self.map_file_name, file_name)
        # print "tsx filename: ", file_name
        # would be more elegant to use  "with open(file_name, "rb") as file:" 
        # but that is python 2.6
        file = None
        try:
            file = open(file_name, "rb")
            dom = minidom.parseString(file.read())
        finally:
            if file:
                file.close()
        for node in self._get_nodes(dom.childNodes, 'tileset'):
            tile_set = self._get_tile_set(node, tile_set, file_name)
            break
        return tile_set

    def _get_tile_set(self, tile_set_node, tile_set, base_path):
        for node in self._get_nodes(tile_set_node.childNodes, u'image'):
            self._build_tile_set_image(node, tile_set, base_path)
        for node in self._get_nodes(tile_set_node.childNodes, u'tile'):
            self._build_tile_set_tile(node, tile_set)
        self._set_attributes(tile_set_node, tile_set)
        return tile_set

    def _build_tile_set_image(self, image_node, tile_set, base_path):
        image = TileImage()
        self._set_attributes(image_node, image)
        # id of TileImage has to be set! -> Tile.TileImage will only have id set
        for node in self._get_nodes(image_node.childNodes, u'data'):
            self._set_attributes(node, image)
            image.content = node.childNodes[0].nodeValue
        image.source = self._get_abs_path(base_path, image.source) # ISSUE 5
        tile_set.images.append(image)

    def _get_abs_path(self, base, relative):
        if os.path.isabs(relative):
            return relative
        if os.path.isfile(base):
            base = os.path.dirname(base)
        return os.path.abspath(os.path.join(base, relative))

    def _build_tile_set_tile(self, tile_set_node, tile_set):
        tile = Tile()
        self._set_attributes(tile_set_node, tile)
        for node in self._get_nodes(tile_set_node.childNodes, u'image'):
            self._build_tile_set_tile_image(node, tile)
        tile_set.tiles.append(tile)

    def _build_tile_set_tile_image(self, tile_node, tile):
        tile_image = TileImage()
        self._set_attributes(tile_node, tile_image)
        for node in self._get_nodes(tile_node.childNodes, u'data'):
            self._set_attributes(node, tile_image)
            tile_image.content = node.childNodes[0].nodeValue
        tile.images.append(tile_image)

    def _build_layer(self, layer_node, world_map):
        layer = TileLayer()
        self._set_attributes(layer_node, layer)
        for node in self._get_nodes(layer_node.childNodes, u'data'):
            self._set_attributes(node, layer)
            if layer.encoding:
                layer.encoded_content = node.lastChild.nodeValue
            else:
                #print 'has childnodes', node.hasChildNodes()
                layer.encoded_content = []
                for child in node.childNodes:
                    if child.nodeType == Node.ELEMENT_NODE and \
                                                    child.nodeName == "tile":
                        val = child.attributes["gid"].nodeValue
                        #print child, val
                        layer.encoded_content.append(val)
        world_map.layers.append(layer)

    def _build_world_map(self, world_node):
        world_map = TileMap()
        self._set_attributes(world_node, world_map)
        if world_map.version != u"1.0":
            raise VersionError(u'this parser was made for maps of version 1.0, found version %s' % world_map.version)
        for node in self._get_nodes(world_node.childNodes, u'tileset'):
            self._build_tile_set(node, world_map)
        for node in self._get_nodes(world_node.childNodes, u'layer'):
            self._build_layer(node, world_map)
        for node in self._get_nodes(world_node.childNodes, u'objectgroup'):
            self._build_object_groups(node, world_map)
        return world_map

    def _build_object_groups(self, object_group_node, world_map):
        object_group = MapObjectGroupLayer()
        self._set_attributes(object_group_node,  object_group)
        for node in self._get_nodes(object_group_node.childNodes, u'object'):
            tiled_object = MapObject()
            self._set_attributes(node, tiled_object)
            for img_node in self._get_nodes(node.childNodes, u'image'):
                tiled_object.image_source = \
                                        img_node.attributes[u'source'].nodeValue
            object_group.objects.append(tiled_object)
        # ISSUE 9
        world_map.layers.append(object_group)

    # -- helpers -- #
    def _get_nodes(self, nodes, name):
        for node in nodes:
            if node.nodeType == Node.ELEMENT_NODE and node.nodeName == name:
                yield node

    def _set_attributes(self, node, obj):
        attrs = node.attributes
        for attr_name in attrs.keys():
            setattr(obj, attr_name, attrs.get(attr_name).nodeValue)
        self._get_properties(node, obj)

    def _get_properties(self, node, obj):
        props = {}
        for properties_node in self._get_nodes(node.childNodes, u'properties'):
            for property_node in self._get_nodes(properties_node.childNodes, u'property'):
                try:
                    props[property_node.attributes[u'name'].nodeValue] = \
                                    property_node.attributes[u'value'].nodeValue
                except KeyError:
                    props[property_node.attributes[u'name'].nodeValue] = \
                                            property_node.lastChild.nodeValue
        obj.properties.update(props)


    # -- parsers -- #
    def parse(self, file_name):
        u"""
        Parses the given map. Does no decoding nor loading of the data.
        :return: instance of TileMap
        """
        # would be more elegant to use  
        # "with open(file_name, "rb") as tmx_file:" but that is python 2.6
        self.map_file_name = os.path.abspath(file_name)
        tmx_file = None
        try:
            tmx_file = open(self.map_file_name, "rb")
            dom = minidom.parseString(tmx_file.read())
        finally:
            if tmx_file:
                tmx_file.close()
        for node in self._get_nodes(dom.childNodes, 'map'):
            world_map = self._build_world_map(node)
            break
        world_map.map_file_name = self.map_file_name
        world_map.convert()
        return world_map

    def parse_decode(self, file_name):
        u"""
        Parses the map but additionally decodes the data.
        :return: instance of TileMap
        """
        world_map = self.parse(file_name)
        world_map.decode()
        return world_map


#  -----------------------------------------------------------------------------

class AbstractResourceLoader(object):
    """
    Abstract base class for the resource loader.

    """

    FLIP_X = 1 << 31
    FLIP_Y = 1 << 30

    def __init__(self):
        self.indexed_tiles = {} # {gid: (offsetx, offsety, image}
        self.world_map = None
        self._img_cache = {}

    def _load_image(self, filename, colorkey=None): # -> image
        u"""
        Load a single image.

        :Parameters:
            filename : string
                Path to the file to be loaded.
            colorkey : tuple
                The (r, g, b) color that should be used as colorkey 
                (or magic color).
                Default: None

        :rtype: image

        """
        raise NotImplementedError(u'This should be implemented in a inherited class')

    def _load_image_file_like(self, file_like_obj, colorkey=None): # -> image
        u"""
        Load a image from a file like object.

        :Parameters:
            file_like_obj : file
                This is the file like object to load the image from.
            colorkey : tuple
                The (r, g, b) color that should be used as colorkey 
                (or magic color).
                Default: None

        :rtype: image
        """
        raise NotImplementedError(u'This should be implemented in a inherited class')

    def _load_image_parts(self, filename, margin, spacing, tilewidth, tileheight, colorkey=None): #-> [images]
        u"""
        Load different tile images from one source image.

        :Parameters:
            filename : string
                Path to image to be loaded.
            margin : int
                The margin around the image.
            spacing : int
                The space between the tile images.
            tilewidth : int
                The width of a single tile.
            tileheight : int
                The height of a single tile.
            colorkey : tuple
                The (r, g, b) color that should be used as colorkey 
                (or magic color).
                Default: None

        Luckily that iteration is so easy in python::

            ...
            w, h = image_size
            for y in xrange(margin, h, tileheight + spacing):
                for x in xrange(margin, w, tilewidth + spacing):
                    ...

        :rtype: a list of images
        """
        raise NotImplementedError(u'This should be implemented in a inherited class')

    def load(self, tile_map):
        u"""
        """
        self.world_map = tile_map
        for tile_set in tile_map.tile_sets:
            # do images first, because tiles could reference it
            for img in tile_set.images:
                if img.source:
                    self._load_image_from_source(tile_map, tile_set, img)
                else:
                    tile_set.indexed_images[img.id] = self._load_tile_image(img)
            # tiles
            for tile in tile_set.tiles:
                for img in tile.images:
                    if not img.content and not img.source:
                        # only image id set
                        indexed_img = tile_set.indexed_images[img.id]
                        self.indexed_tiles[int(tile_set.firstgid) + int(tile.id)] = (0, 0, indexed_img)
                    else:
                        if img.source:
                            self._load_image_from_source(tile_map, tile_set, img)
                        else:
                            indexed_img = self._load_tile_image(img)
                            self.indexed_tiles[int(tile_set.firstgid) + int(tile.id)] = (0, 0, indexed_img)

    def _load_image_from_source(self, tile_map, tile_set, a_tile_image):
        # relative path to file
        img_path = os.path.join(os.path.dirname(tile_map.map_file_name), \
                                                            a_tile_image.source)
        tile_width = int(tile_map.tilewidth)
        tile_height = int(tile_map.tileheight)
        if tile_set.tileheight:
            tile_width = int(tile_set.tilewidth)
        if tile_set.tilewidth:
            tile_height = int(tile_set.tileheight)
        offsetx = 0
        offsety = 0
        # the offset is used for pygame because the origin is topleft in pygame
        if tile_height > tile_map.tileheight:
            offsety = tile_height - tile_map.tileheight
        idx = 0
        for image in self._load_image_parts(img_path, \
                    tile_set.margin, tile_set.spacing, \
                    tile_width, tile_height, a_tile_image.trans):
            self.indexed_tiles[int(tile_set.firstgid) + idx] = \
                                                    (offsetx, -offsety, image)
            idx += 1

    def _load_tile_image(self, a_tile_image):
        img_str = a_tile_image.content
        if a_tile_image.encoding:
            if a_tile_image.encoding == u'base64':
                img_str = decode_base64(a_tile_image.content)
            else:
                raise Exception(u'unknown image encoding %s' % a_tile_image.encoding)
        sio = StringIO.StringIO(img_str)
        new_image = self._load_image_file_like(sio, a_tile_image.trans)
        return new_image

#  -----------------------------------------------------------------------------

