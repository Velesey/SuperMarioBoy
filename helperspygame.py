# -*- coding: utf-8 -*-

"""

TileMap loader for python for Tiled, a generic tile map editor
from http://mapeditor.org/ .
It loads the \*.tmx files produced by Tiled.

This is the code that helps using the tmx files using pygame. In this
module there is a pygame specific loader and renderer.

"""

# Versioning scheme based on:
# http://en.wikipedia.org/wiki/Versioning#Designating_development_stage
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
from __future__ import division

__revision__ = "$Rev: 107 $"
__version__ = "3.0.0." + __revision__[6:-2]
__author__ = u'DR0ID @ 2009-2011'


#  -----------------------------------------------------------------------------

from math import ceil

import pygame

import tmxreader

#  -----------------------------------------------------------------------------

#  -----------------------------------------------------------------------------

class ResourceLoaderPygame(tmxreader.AbstractResourceLoader):
    """
    Resource loader for pygame. Loads the images as pygame.Surfaces and saves
    them in the variable indexed_tiles.


    Example::

        res_loader = ResourceLoaderPygame()
        # tile_map loaded the the TileMapParser.parse() method
        res_loader.load(tile_map)

    """

    def __init__(self):
        tmxreader.AbstractResourceLoader.__init__(self)

    def load(self, tile_map):
        tmxreader.AbstractResourceLoader.load(self, tile_map)
        # delete the original images from memory, they are all saved as tiles
        self._img_cache.clear()
        # ISSUE 17: flipped tiles
        for layer in self.world_map.layers:
            if not layer.is_object_group:
                for gid in layer.decoded_content:
                    if gid not in self.indexed_tiles:
                        if gid & self.FLIP_X or gid & self.FLIP_Y:
                            image_gid = gid & ~(self.FLIP_X | self.FLIP_Y)
                            offx, offy, img = self.indexed_tiles[image_gid]
                            img = img.copy()
                            img = pygame.transform.flip(img, \
                                                    bool(gid & self.FLIP_X), \
                                                    bool(gid & self.FLIP_Y))
                            self.indexed_tiles[gid] = (offx, offy, img)

    def _load_image_parts(self, filename, margin, spacing, \
                          tile_width, tile_height, colorkey=None): #-> [images]
        source_img = self._load_image(filename, colorkey)
        width, height = source_img.get_size()
        # ISSUE 16
        # if the image size does not match a multiple of tile_width or
        # tile_height it will mess up the number of tiles resulting in
        # wrong GID's for the tiles
        width = (width // tile_width) * tile_width
        height = (height // tile_height) * tile_height
        images = []
        for ypos in xrange(margin, height, tile_height + spacing):
            for xpos in xrange(margin, width, tile_width + spacing):
                img_part = self._load_image_part(filename, xpos, ypos, \
                                            tile_width, tile_height, colorkey)
                images.append(img_part)
        return images

    def _load_image_part(self, filename, xpos, ypos, width, height, \
                                                                colorkey=None):
        """
        Loads a image from a sprite sheet.
        """
        source_img = self._load_image(filename, colorkey)
        ## ISSUE 4:
        ##  The following usage seems to be broken in pygame (1.9.1.):
        ##  img_part = pygame.Surface((tile_width, tile_height), 0, source_img)
        img_part = pygame.Surface((width, height), \
                                    source_img.get_flags(), \
                                    source_img.get_bitsize())
        source_rect = pygame.Rect(xpos, ypos, width, height)

        ## ISSUE 8:
        ## Set the colorkey BEFORE we blit the source_img
        if colorkey:
            img_part.set_colorkey(colorkey, pygame.RLEACCEL)
            img_part.fill(colorkey)

        img_part.blit(source_img, (0, 0), source_rect)

        return img_part

    def _load_image_file_like(self, file_like_obj, colorkey=None): # -> image
        # pygame.image.load can load from a path and from a file-like object
        # that is why here it is redirected to the other method
        return self._load_image(file_like_obj, colorkey)

    def _load_image(self, filename, colorkey=None):
        img = self._img_cache.get(filename, None)
        if img is None:
            img = pygame.image.load(filename)
            self._img_cache[filename] = img
        if colorkey:
            img.set_colorkey(colorkey, pygame.RLEACCEL)
        return img

    # def get_sprites(self):
        # pass



#  -----------------------------------------------------------------------------
#  -----------------------------------------------------------------------------
class SpriteLayerNotCompatibleError(Exception): pass

class SpriteLayer(object):
    """
    The SpriteLayer class. This class is used by the RendererPygame.


    """

    class Sprite(object):
        """
        The Sprite class used by the SpriteLayer class and the RendererPygame.

        """
        def __init__(self, image, rect, source_rect=None, flags=0, key=None):
            """
            Constructor.
            :Parameters:
                image : pygame.Surface
                    the image of this sprite
                rect : pygame.Rect
                    the rect used when drawing
                source_rect : pygame.Rect
                    source area rect, defaults to None
                flags : int
                    flags for the blit method, defaults to 0
                key : any
                    used internally for collapsing sprites

            """
            self.image = image
            # TODO: dont use a rect for position
            self.rect = rect # blit rect
            self.source_rect = source_rect
            self.flags = flags
            self.is_flat = False
            self.z = 0
            self.key = key

        def get_draw_cond(self):
            """
            Defines if the sprite lays on the floor or if it is up-right.

            :returns:
                The bottom y coordinate so the sprites can be sorted in right
                draw order.
            """
            if self.is_flat:
                return self.rect.top + self.z
            else:
                return self.rect.bottom

    def __init__(self, tile_layer_idx, resource_loader):
        """

        :Parameters:
            tile_layer_idx : int
                Index of the tile layer to build upon
            resource_loader : ResourceLoaderPygame
                Instance of the ResourceLoaderPygame class which has loaded
                the resouces
        """
        self._resource_loader = resource_loader
        _world_map = self._resource_loader.world_map
        self.layer_idx = tile_layer_idx
        _layer = _world_map.layers[tile_layer_idx]

        self.tilewidth = _world_map.tilewidth
        self.tileheight = _world_map.tileheight
        self.num_tiles_x = _world_map.width
        self.num_tiles_y = _world_map.height
        self.position_x = _layer.x
        self.position_y = _layer.y


        self._level = 1

        # TODO: change scale attributes to properties?
        self.scale_x = 1.0
        self.scale_y = 1.0

        # TODO: either change paralax_* attributes to properties
        # or make them private
        self.paralax_factor_x = 1.0
        self.paralax_factor_y = 1.0

        self.sprites = []
        self.is_object_group = _layer.is_object_group
        self.visible = _layer.visible
        self.bottom_margin = 0
        self._bottom_margin = 0


        # init data to default
        # self.content2D = []
        # generate the needed lists
        # for xpos in xrange(self.num_tiles_x):
            # self.content2D.append([None] * self.num_tiles_y)

        self.content2D = [None] * self.num_tiles_y
        for ypos in xrange(self.num_tiles_y):
            self.content2D[ypos] = [None] * self.num_tiles_x

        # fill them
        _img_cache = {}
        _img_cache["hits"] = 0
        for ypos_new in xrange(0, self.num_tiles_y):
            for xpos_new in xrange(0, self.num_tiles_x):
                coords = self._get_list_of_neighbour_coord(xpos_new, ypos_new, \
                                        1, self.num_tiles_x, self.num_tiles_y)
                if coords:
                    key, sprites = SpriteLayer._get_sprites_fromt_tiled_layer(\
                            coords, _layer, self._resource_loader.indexed_tiles)

                    sprite = None
                    if sprites:
                        sprite = SpriteLayer._union_sprites(sprites, key, \
                                                                    _img_cache)
                        if sprite.rect.height > self._bottom_margin:
                            self._bottom_margin = sprite.rect.height

                    self.content2D[ypos_new][xpos_new] = sprite
        self.bottom_margin = self._bottom_margin
        if __debug__:
            print '%s: Sprite Cache hits: %d' % \
                                (self.__class__.__name__, _img_cache["hits"])
        del _img_cache

    def get_collapse_level(self):
        """
        The level of collapsing.

        :returns:
            The collapse level.
        """
        return self._level

    # TODO: test scale
    @staticmethod
    def scale(layer_orig, scale_w, scale_h): # -> sprite_layer
        """
        Scales a layer and returns a new, scaled SpriteLayer.

        :Note: This method is slow and inefficient

        :Parameters:
            scale_w : float
                Width scale factor in range (0, ...]
            scale_h : float
                Height scale factor in range (0, ...]
        """
        if layer_orig.is_object_group:
            return layer

        layer = SpriteLayer(layer_orig.layer_idx, layer_orig._resource_loader)

        layer.tilewidth = layer_orig.tilewidth * scale_w
        layer.tileheight = layer_orig.tileheight * scale_h
        layer.position_x = layer_orig.position_x
        layer.position_y = layer_orig.position_y


        layer._level = layer_orig._level

        layer.paralax_factor_x = layer_orig.paralax_factor_x
        layer.paralax_factor_y = layer_orig.paralax_factor_y
        layer.sprites = layer_orig.sprites
        layer.is_object_group = layer_orig.is_object_group
        layer.visible = layer_orig.visible
        layer.scale_x = scale_w
        layer.scale_y = scale_h

        layer.content2D = [0] * len(layer_orig.content2D)
        for yidx, row in enumerate(layer_orig.content2D):
            layer.content2D[yidx] = [0] * len(row)
            for xidx, sprite in enumerate(row):
                if sprite:
                    w, h = sprite.image.get_size()
                    new_w = w * scale_w
                    new_h = h * scale_h
                    rect = sprite.rect
                    image = sprite.image
                    # prevent fractional numbers and scaling glitches
                    if w != ceil(new_w) or h != ceil(new_h):
                        new_w = ceil(new_w)
                        new_h = ceil(new_h)
                        image = pygame.transform.smoothscale(sprite.image, \
                                                                 (new_w, new_h))
                        x, y = sprite.rect.topleft
                        rect = pygame.Rect(x * scale_w, y * scale_h, \
                                                                new_w, new_h)

                    layer.content2D[yidx][xidx] = \
                                                SpriteLayer.Sprite(image, rect)
                else:
                    layer.content2D[yidx][xidx] = None

        return layer

    # TODO: implement merge
    @staticmethod
    def merge(layers): # -> sprite_layer
        """
        Merges multiple Sprite layers into one. Only SpriteLayers are supported.
        All layers need to be equal in tile size, number of tiles and layer
        position. Otherwise a SpriteLayerNotCompatibleError is raised.

        :Parameters:
            layers : list
                The SpriteLayer to be merged

        :returns: new SpriteLayer with merged tiles

        """
        tile_width = None
        tile_height = None
        num_tiles_x = None
        num_tiles_y = None
        position_x = None
        position_y = None
        new_layer = None

        for layer in layers:
            if layer.is_object_group:
                # skip object group layers
                continue

            assert isinstance(layer, SpriteLayer), "layer is not an instance of SpriteLayer"

            # just use the values from first layer
            tile_width = tile_width if tile_width else layer.tile_width
            tile_height = tile_height if tile_height else layer.tile_height
            num_tiles_x = num_tiles_x if num_tiles_x else layer.num_tiles_x
            num_tiles_y = num_tiles_y if num_tiles_y else layer.num_tiles_y
            position_x = position_x if position_x else layer.position_x
            position_y = position_y if position_y else layer.position_y

            # check they are equal for all layers
            if layer.tile_width != tile_width:
                raise SpriteLayerNotCompatibleError("layers do not have same tile_width")
            if layer.tile_height != tile_height:
                raise SpriteLayerNotCompatibleError("layers do not have same tile_height")
            if layer.num_tiles_x != num_tiles_x:
                raise SpriteLayerNotCompatibleError("layers do not have same number of tiles in x direction")
            if layer.num_tiles_y != num_tiles_y:
                raise SpriteLayerNotCompatibleError("layers do not have same number of tiles in y direction")
            if layer.position_x != position_x:
                raise SpriteLayerNotCompatibleError("layers are not at same position in x")
            if layer.position_y != position_y:
                raise SpriteLayerNotCompatibleError("layers are not at same position in y")

            if new_layer is None:
                new_layer = SpriteLayer(-2, layer._resource_loader)

            for ypos_new in xrange(0, num_tiles_y):
                for xpos_new in xrange(0, num_tiles_x):
                    sprite = layer.content2D[ypos_new][xpos_new]
                    if sprite:
                        new_sprite = new_layer.content2D[ypos_new][xpos_new]
                        if new_sprite:
                            assert sprite.rect.topleft == new_sprite.rect.topleft
                            assert sprite.rect.size == new_sprite.rect.size
                            new_sprite.image.blit(sprite.image, (0, 0), \
                                            sprite.source_rect, sprite.flags)
                        else:
                            new_sprite = sprite
                        new_layer.content2D[ypos_new][xpos_new] = new_sprite

        return new_layer


    @staticmethod
    def collapse(layer):
        """
        Makes 1 tile out of 4. The idea behind is that fewer tiles
        are faster to render, but that is not always true.
        Grouping them together into one bigger sprite is one way to get fewer
        sprites.

        :not: This only works for static layers without any dynamic sprites.

        :note: use with caution

        :Parameters:
            laser : SpriteLayer
                The layer to collapse

        :returns: new SpriteLayer with fewer sprites but double the size.

        """

        #   +    0'        1'        2'
        #        0    1    2    3    4
        #   0' 0 +----+----+----+----+
        #        |    |    |    |    |
        #      1 +----+----+----+----+
        #        |    |    |    |    |
        #   1' 2 +----+----+----+----+
        #        |    |    |    |    |
        #      3 +----+----+----+----+
        #        |    |    |    |    |
        #   2' 4 +----+----+----+----+

        if layer.is_object_group:
            return layer
        level = 2

        new_tilewidth = layer.tilewidth * level
        new_tileheight = layer.tileheight * level
        new_num_tiles_x = int(layer.num_tiles_x / level)
        new_num_tiles_y = int(layer.num_tiles_y / level)
        if new_num_tiles_x * level < layer.num_tiles_x:
            new_num_tiles_x += 1
        if new_num_tiles_y * level < layer.num_tiles_y:
            new_num_tiles_y += 1

        # print "old size", layer.num_tiles_x, layer.num_tiles_y
        # print "new size", new_num_tiles_x, new_num_tiles_y

        _content2D = [None] * new_num_tiles_y
        # generate the needed lists

        for ypos in xrange(new_num_tiles_y):
            _content2D[ypos] = [None] * new_num_tiles_x

        # fill them
        _img_cache = {}
        _img_cache["hits"] = 0
        for ypos_new in xrange(0, new_num_tiles_y):
            for xpos_new in xrange(0, new_num_tiles_x):
                coords = SpriteLayer._get_list_of_neighbour_coord(\
                                        xpos_new, ypos_new, level, \
                                        layer.num_tiles_x, layer.num_tiles_y)
                if coords:
                    sprite = SpriteLayer._get_sprite_from(coords, layer, \
                                                                    _img_cache)
                    _content2D[ypos_new][xpos_new] = sprite

        # print "len content2D:", len(self.content2D)
        # TODO: separate constructor from init code (here the layer is parsed
        #       for nothing, content2D will be replaced)
        new_layer = SpriteLayer( layer.layer_idx, layer._resource_loader)

        new_layer.tilewidth  = new_tilewidth
        new_layer.tileheight = new_tileheight
        new_layer.num_tiles_x = new_num_tiles_x
        new_layer.num_tiles_y = new_num_tiles_y
        new_layer.content2D = _content2D

        # HACK:
        new_layer._level = layer._level * 2

        if __debug__ and level > 1:
            print '%s: Sprite Cache hits: %d' % ("collapse", _img_cache["hits"])
        return new_layer

    @staticmethod
    def _get_list_of_neighbour_coord(xpos_new, ypos_new, level, \
                                                    num_tiles_x, num_tiles_y):
        """
        Finds the neighbours of a tile and returns them

        :Parameters:
            xpos_new : int
                x position
            ypos_new : int
                y position
            level : int
                collapse level because this uses original tiles
            num_tiles_x : int
                number of tiles in x direction
            num_tiles_y : int
                number of tiles in y direction
        :Returns:
            list of coordinates of the neighbour tiles
        """
        xpos = xpos_new * level
        ypos = ypos_new * level

        coords = []
        for y in xrange(ypos, ypos + level):
            for x in xrange(xpos, xpos + level):
                if x <= num_tiles_x and y <= num_tiles_y:
                    coords.append((x, y))
        return coords

    @staticmethod
    def _union_sprites(sprites, key, _img_cache):
        """
        Unions sprites into one big one.

        :Parameters:
            sprites : list
                list of sprites to union
            key : iterable
                key of the sprite, internal use only
            _img_cache : dict
                cache dict
        :Returns:
            new Sprite that unites all the given sprites.
        """
        key = tuple(key)

        # dont copy to a new image if only one sprite is in sprites
        # (reduce memory usage)
        # NOTE: this messes up the cache hits (only on non-collapsed maps)
        if len(sprites) == 1:
            sprite = sprites[0]
            sprite.key = key
            return sprite

        # combine found sprites into one sprite
        rect = sprites[0].rect.unionall(sprites)

        # cache the images to save memory
        if key in _img_cache:
            image = _img_cache[key]
            _img_cache["hits"] = _img_cache["hits"] + 1
        else:
            # make new image
            image = pygame.Surface(rect.size, pygame.SRCALPHA | pygame.RLEACCEL)
            image.fill((0, 0, 0, 0))
            x, y = rect.topleft
            for spr in sprites:
                image.blit(spr.image, spr.rect.move(-x, -y))

            _img_cache[key] = image

        return SpriteLayer.Sprite(image, rect, key=key)

    @staticmethod
    def _get_sprites_fromt_tiled_layer(coords, layer, indexed_tiles):
        """
        Get the sprites at the given coordinates from a tiled layer.

        :Parameters:
            coords : list
                list of coordinates tuples
            layer : TiledLayer
                layer to extract the sprites from
            indexed_tiles : dict
                indexed tiles list loaded by the resource loader.

        :Returns:
            (keys, sprites) the new keys and sprites

        """
        sprites = []
        key = []
        for xpos, ypos in coords:
            ## ISSUE 14: maps was displayed only sqared because wrong
            ## boundary checks
            if xpos >= len(layer.content2D) or \
                                ypos >= len(layer.content2D[xpos]):
                # print "CONTINUE", xpos, ypos
                key.append(-1) # border and corner cases!
                continue
            idx = layer.content2D[xpos][ypos]
            if idx:
                offx, offy, img = indexed_tiles[idx]
                world_x = xpos * layer.tilewidth + offx
                world_y = ypos * layer.tileheight + offy
                w, h = img.get_size()
                rect = pygame.Rect(world_x, world_y, w, h)
                sprite = SpriteLayer.Sprite(img, rect, key=idx)
                key.append(idx)
                sprites.append(sprite)
            else:
                key.append(-1)
        return key, sprites

    @staticmethod
    def _get_sprite_from(coords, layer, _img_cache):
        """
        Get one sprite for the given coordinates on the given layer.

        :Parameters:
            coords : list
                tuples of coordinates (x, y)
            layer : SpriteLayer
                the layer to get the united sprite from
            _img_cache : dict
                dict for caching, internal use only

        :returns:
            a single sprite, uniting all given sprites on the fiven coordinates.

        """
        sprites = []
        key = []
        for xpos, ypos in coords:
            if ypos >= len(layer.content2D) or \
                                    xpos >= len(layer.content2D[ypos]):
                # print "CONTINUE", xpos, ypos
                key.append(-1) # border and corner cases!
                continue
            idx = layer.content2D[ypos][xpos]
            if idx:
                sprite = idx
                key.append(sprite.key)
                sprites.append(sprite)
            else:
                key.append(-1)

        if sprites:
            sprite = SpriteLayer._union_sprites(sprites, key, _img_cache)

            if __debug__:
                x, y = sprite.rect.topleft
                pygame.draw.rect(sprite.image, (255, 0, 0), \
                                    sprite.rect.move(-x, -y), \
                                    layer.get_collapse_level())

            del sprites
            return sprite

        return None

    def add_sprite(self, sprite):
        """
        Add dynamic sprite to this layer.

        :Parameters:
            sprite : SpriteLayer.Sprite
                sprite to add
        """
        self.sprites.append(sprite)
        if sprite.rect.height > self.bottom_margin:
            self.bottom_margin = sprite.rect.height

    def add_sprites(self, sprites):
        """
        Add multiple dynamic sprites to this layer.

        :Parameters:
            sprites : list
                list of SpriteLayer.Sprite to add
        """
        for sprite in sprites:
            self.add_sprite(sprite)

    def remove_sprite(self, sprite):
        """
        Removes a dynamic sprite from this layer.

        :Parameters:
            sprite : SpriteLayer.Sprite
                sprite to remove
        """
        if sprite in self.sprites:
            self.sprites.remove(sprite)

        self.bottom_margin = self._bottom_margin
        for spr in self.sprites:
            if spr.rect.height > self.bottom_margin:
                self.bottom_margin = spr.rect.height

    def remove_sprites(self, sprites):
        """
        Remove multiple sprites at once.

        :Parameters:
            sprites : list
                list of SpriteLayer.Sprite to remove

        """
        for sprite in sprites:
            self.remove_sprite(sprite)

    def contains_sprite(self, sprite):
        """
        Check if the given sprites is already in this layer.

        :Parameters:
            sprite : SpriteLayer.Sprite
                sprite to check

        :Returns:
            bool, true if sprite is in this layer
        """
        if sprite in self.sprites:
            return True
        return False

    def has_sprites(self):
        """
        Checks if this layer has dynamic sprites at all.

        :Returns: bool, true if it contains at least 1 dynamic sprite.
        """
        return (len(self.sprites) > 0)

    def set_layer_paralax_factor(self, factor_x=1.0, factor_y=None):
        """
        Set the paralax factor. This is for paralax scrolling this layer.
        Values x < 0.0 will make the layer scroll in opposite direction
        Value x == 0.0 makes the layer fix to the screen (wont scroll)
        Values 0.0 < x < 1.0 will make scroll the layer slower.
        Value x == 1.0 is default and make scroll the layer normal.
        Values x > 1.0 make scroll the layer faster than normal

        :Parameters:
            factor_x : float
                Paralax factor in x direction. Defaults to 1.0
            factor_y : float
                Paralax factor in y direction. If this is None then it will have
                the same value as the factor_x argument.
        """
        self.paralax_factor_x = factor_x
        if factor_y:
            self.paralax_factor_y = factor_y
        else:
            self.paralax_factor_y = factor_x

    def get_layer_paralax_factor_x(self):
        """
        Retrieve the current x paralax factor.

        :Returns:
            returns the current x paralax factor.
        """
        return self.paralax_factor_x

    def get_layer_paralax_factor_y(self):
        """
        Retrieve the current y paralax factor.

        :Returns:
            returns the current y paralax factor.
        """
        return self.paralax_factor_y

#  -----------------------------------------------------------------------------

def get_layers_from_map(resource_loader):
    """
    Creates SpriteLayers out of the map.

    :Parameters:
        resource_loader : ResourceLoaderPygame
            a resource loader instance

    :Returns: list of SpriteLayers
    """
    layers = []
    for idx, layer in enumerate(resource_loader.world_map.layers):
        layers.append(get_layer_at_index(idx, resource_loader))
    return layers

def get_layer_at_index(layer_idx, resource_loader):
    """
    Creates one SpriteLayer from index out of the map.

    :Parameters:
        layer_idx : int
            Index of the layer to create.
        resource_loader : ResourceLoaderPygame
            a resource loader instance

    :Returns: a SpriteLayer instance

    """
    layer = resource_loader.world_map.layers[layer_idx]
    if layer.is_object_group:
        return layer
    return SpriteLayer(layer_idx, resource_loader)

#  -----------------------------------------------------------------------------

class RendererPygame(object):
    """
    A renderer for pygame. Should be fast enough for most purposes.

    Example::

        # init
        sprite_layers = get_layers_from_map(resources)
        renderer = RendererPygame()

        # in main loop
        while running:

            # move camera
            renderer.set_camera_position(x, y)

            # draw layers
            for sprite_layer in sprite_layers:
                renderer.render_layer(screen, sprite_layer, clip_sprites)

    """

    def __init__(self):
        """
        Constructor.

        """
        self._cam_rect = pygame.Rect(0, 0, 10, 10)
        self._margin = (0, 0, 0, 0) # left, right, top, bottom

    def set_camera_position(self, world_pos_x, world_pos_y, alignment='center'):
        """
        Set the camera position in the world.

        :Parameters:
            world_pos_x : int
                position in x in world coordinates
            world_pos_y : int
                position in y in world coordinates
            alignment : string
                defines to which part of the cam rect the position belongs,
                can be any pygame.Rect
                attribute: 'center', 'topleft', 'topright', ...
        """
        setattr(self._cam_rect, alignment, (world_pos_x, world_pos_y))
        self.set_camera_margin(*self._margin)

    def set_camera_position_and_size(self, world_pos_x, world_pos_y, \
                                   width, height, alignment='center'):
        """
        Set the camera position and size in the world.

        :Parameters:
            world_pos_x : int
                Position in x in world coordinates.
            world_pos_y : int
                Position in y in world coordinates.
            witdh : int
                With of the camera rect (the rendered area).
            height : int
                The height of the camera rect (the rendered area).
            alignment : string
                Defines to which part of the cam rect the position belongs,
                can be any pygame.Rect
                attribute: 'center', 'topleft', 'topright', ...

        """
        self._cam_rect.width = width
        self._cam_rect.height = height
        setattr(self._cam_rect, alignment, (world_pos_x, world_pos_y))
        self.set_camera_margin(*self._margin)

    def set_camera_rect(self, cam_rect_world_coord):
        """
        Set the camera position and size using a rect in world coordinates.

        :Parameters:
            cam_rect_world_coord : pygame.Rect
                A rect describing the cameras position and size in the world.

        """
        self._cam_rect = cam_rect_world_coord
        self.set_camera_margin(*self._margin)

    def set_camera_margin(self, margin_left, margin_right, margin_top, margin_bottom):
        """
        Set the margin around the camera (in pixels).

        :Parameters:
            margin_left : int
                number of pixels of the left side marging
            margin_right : int
                number of pixels of the right side marging
            margin_top : int
                number of pixels of the top side marging
            margin_bottom : int
                number of pixels of the left bottom marging

        """
        self._margin = (margin_left, margin_right, margin_top, margin_bottom)
        self._render_cam_rect = pygame.Rect(self._cam_rect)
        # adjust left margin
        self._render_cam_rect.left = self._render_cam_rect.left - margin_left
        # adjust right margin
        self._render_cam_rect.width = self._render_cam_rect.width + \
                                                    margin_left + margin_right
        # adjust top margin
        self._render_cam_rect.top = self._render_cam_rect.top - margin_top
        # adjust bottom margin
        self._render_cam_rect.height = self._render_cam_rect.height + \
                                                    margin_top + margin_bottom
        self._render_cam_rect.left = self._cam_rect.left - margin_left
        self._render_cam_rect.top = self._cam_rect.top - margin_top

    def render_layer(self, surf, layer, clip_sprites=True, \
                                    sort_key=lambda spr: spr.get_draw_cond()):
        """
        Renders a layer onto the given surface.

        :Parameters:
            surf : Surface
                Surface to render onto.
            layer : SpriteLayer
                The layer to render. Invisible layers will be skipped.
            clip_sprites : boolean
                Optional, defaults to True. Clip the sprites of this layer to
                only draw the ones intersecting the visible part of the world.
            sort_key : function
                Optional: The sort function for the parameter 'key' of the sort
                method of the list.

        """
        if layer.visible:

            if layer.is_object_group:
                return

            if layer.bottom_margin > self._margin[3]:
                left, right, top, bottom = self._margin
                self.set_camera_margin(left, right, top, layer.bottom_margin)

            # optimizations
            surf_blit = surf.blit
            layer_content2D = layer.content2D

            tile_h = layer.tileheight

                        # self.paralax_factor_y = 1.0
            # self.paralax_center_x = 0.0
            cam_rect = self._render_cam_rect
            # print 'cam rect:', self._cam_rect
            # print 'render r:', self._render_cam_rect

            cam_world_pos_x = cam_rect.left * layer.paralax_factor_x + \
                                                                layer.position_x
            cam_world_pos_y = cam_rect.top * layer.paralax_factor_y + \
                                                                layer.position_y

            # camera bounds, restricting number of tiles to draw
            left = int(round(float(cam_world_pos_x) // layer.tilewidth))
            right = int(round(float(cam_world_pos_x + cam_rect.width) // \
                                            layer.tilewidth)) + 1
            top = int(round(float(cam_world_pos_y) // tile_h))
            bottom = int(round(float(cam_world_pos_y + cam_rect.height) // \
                                            tile_h)) + 1

            left = left if left > 0 else 0
            right = right if right < layer.num_tiles_x else layer.num_tiles_x
            top = top if top > 0 else 0
            bottom = bottom if bottom < layer.num_tiles_y else layer.num_tiles_y

            # sprites
            spr_idx = 0
            len_sprites = 0
            all_sprites = layer.sprites
            if all_sprites:
                # TODO: make filter visible sprites optional (maybe sorting too)
                # use a marging around it
                if clip_sprites:
                    sprites = [all_sprites[idx] \
                                for idx in cam_rect.collidelistall(all_sprites)]
                else:
                    sprites = all_sprites

                # could happend that all sprites are not visible by the camera
                if sprites:
                    if sort_key:
                        sprites.sort(key=sort_key)
                    sprite = sprites[0]
                    len_sprites = len(sprites)


            # render
            for ypos in range(top, bottom):
                # draw sprites in this layer
                # (skip the ones outside visible area/map)
                y = ypos + 1
                while spr_idx < len_sprites and sprite.get_draw_cond() <= \
                                                                    y * tile_h:
                    surf_blit(sprite.image, \
                                sprite.rect.move(-cam_world_pos_x, \
                                                 -cam_world_pos_y - sprite.z),\
                                sprite.source_rect, \
                                sprite.flags)
                    spr_idx += 1
                    if spr_idx < len_sprites:
                        sprite = sprites[spr_idx]
                # next line of the map
                for xpos in range(left, right):
                    tile_sprite = layer_content2D[ypos][xpos]
                    # print '?', xpos, ypos, tile_sprite
                    if tile_sprite:
                        surf_blit(tile_sprite.image, \
                                    tile_sprite.rect.move( -cam_world_pos_x, \
                                                           -cam_world_pos_y), \
                                    tile_sprite.source_rect, \
                                    tile_sprite.flags)

    def pick_layer(self, layer, screen_x, screen_y):
        """
        Returns the sprite at the given screen position or None regardless of
        the layers visibility.

        :Note: This does not work wir object group layers.

        :Parameters:
            layer : SpriteLayer
                the layer to pick from
            screen_x : int
                The screen position in x direction.
            screen_y : int
                The screen position in y direction.

        :Returns:
            None if there is no sprite or the sprite
            (SpriteLayer.Sprite instance).
        """
        if layer.is_object_group:
            pass
        else:
            world_pos_x, world_pos_y = \
                                   self.get_world_pos(layer, screen_x, screen_y)

            tile_x = int(world_pos_x / layer.tilewidth)
            tile_y = int(world_pos_y / layer.tileheight)

            if 0 <= tile_x < layer.num_tiles_x and \
               0 <= tile_y < layer.num_tiles_y:
                sprite = layer.content2D[tile_y][tile_x]
                if sprite:
                    return sprite
        return None

    def pick_layers_sprites(self, layer, screen_x, screen_y):
        """
        Returns the sprites at the given screen positions or an empty list.
        The sprites are the same order as in the layers.sprites list.

        :Note: This does not work wir object group layers.

        :Parameters:
            layer : SpriteLayer
                the layer to pick from
            screen_x : int
                The screen position in x direction.
            screen_y : int
                The screen position in y direction.

        :Returns:
            A list of sprites or an empty list.
        """
        if layer.is_object_group:
            pass
        else:
            world_pos_x, world_pos_y = \
                                self.get_world_pos(layer, screen_x, screen_y)

            r = pygame.Rect(world_pos_x, world_pos_y, 1, 1)
            indices = r.collidelistall(layer.sprites)
            return [layer.sprites[idx] for idx in indices]
        return []

    def get_world_pos(self, layer, screen_x, screen_y):
        """
        Returns the world coordinates for the given screen location and layer.

        :Note:
            this is important so one can check which entity is there in the
            model (knowing which sprite is there does not help much)

        :Parameters:
            layer : SpriteLayer
                the layer to pick from
            screen_x : int
                The screen position in x direction.
            screen_y : int
                The screen position in y direction.

        :Returns:
            Tuple of world coordinates: (world_x, world_y)

        """
        # TODO: also use layer.x and layer.y offset
        return (screen_x + self._render_cam_rect.x * layer.paralax_factor_x, \
                screen_y + self._render_cam_rect.y * layer.paralax_factor_y)

#  -----------------------------------------------------------------------------





