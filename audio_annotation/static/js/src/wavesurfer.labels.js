'use strict';

/**
 * Purpose:
 *   Add labels of the annotation above the corresponding regions
 * Dependencies:
 *   WaveSurfer (lib/wavesurfer.min.js), WaveSurfer.Regions (src/wavesurfer.regions.js)
 */

WaveSurfer.Labels = {
    style: WaveSurfer.Drawer.style,

    init: function (params) {

        this.params = params;
        this.index_color = this.params.container.slice(-1)

        var wavesurfer = this.wavesurfer = params.wavesurfer;

        if (!this.wavesurfer) {
            throw Error('No WaveSurfer intance provided');
        }

        var drawer = this.drawer = this.wavesurfer.drawer;

        this.container = 'string' == typeof params.container ?
            document.querySelector(params.container) : params.container;

        if (!this.container) {
            throw Error('No container for WaveSurfer timeline');
        }
        this.width = drawer.width;
        this.pixelRatio = this.drawer.params.pixelRatio;
        this.labelsElement = null;
        this.labels = {};
        this.rowHeight = this.params.rowHeight || 20;
        this.maxRows = this.params.maxRows || 2;
        this.height = this.params.height || (this.rowHeight * this.maxRows);
        this.color_pallet = this.params.color_pallet

        // Create & append wrapper element to container
        this.createWrapper(this.params.annotation_labels);
        // Create & append label container element to wrapper element
        // this.render();

        if (this.params.pass_id === '3') {
            this.createwrapperSpeech(this.params.speech_annotations)
        }

        // When the user scrolls in the wavesurfer, make the labels scroll with it
        drawer.wrapper.addEventListener('scroll', function (e) {
            this.updateScroll(e);
        }.bind(this));

        // Replace the label container with a empty one when the wavesurfer is redrawn
        // wavesurfer.on('redraw', this.render.bind(this));
        // Destory the wrapper when the wavesurfer is destroyed
        wavesurfer.on('destroy', this.destroy.bind(this));
        // Add a label when a region is created
        wavesurfer.on('region-created', this.add.bind(this));
        // Update a label when its region is updated
        wavesurfer.on('region-updated', this.rearrange.bind(this));
        // Rearrange labels when a region is deleted
        wavesurfer.on('region-removed', this.rearrange.bind(this));


        this.container = $(this.paramscontainer)[0];
        this.wrapper = $(this.params.label_container)[0];
        this.labelsElement = $("." + this.params.label_container)[0];

    },

    change_container(newcontainer, newwrapper, newlabelsElement) {
        // console.log( $(newcontainer)[0])
        this.container = $(newcontainer)[0]
        this.wrapper = $(newwrapper)[0]
        this.labelsElement = $(newlabelsElement)[0]
        this.index_color = newcontainer.slice(-1)
    },

    // Remove the wrapper element
    destroy: function () {
        this.unAll();
        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
            this.wrapper = null;
        }
    },

    createwrapperSpeech: function (speech_annotations) {
        var my = this;
        my.container = $(".labels" + '00')[0]

        my.wrapper = my.container.appendChild(
            document.createElement('Speech')
        );

        my.style(my.wrapper, {
            display: 'block',
            position: 'relative',
            height: my.height + 'px',
            "border-style": "solid",
            "border-width": "1px",
            "border-color": "black",
        });


        my.style(my.wrapper, {
            "border-bottom": 0,
        })


        if (my.wavesurfer.params.fillParent || my.wavesurfer.params.scrollParent) {
            my.style(my.wrapper, {
                width: '100%',
                overflow: 'hidden',
            });
        }

        my.labelsElement = my.wrapper.appendChild(document.createElement('div'));
        my.labelsElement.className = 'Speech'
        my.style(my.labelsElement, {
            height: my.height + 'px',
            width: my.drawer.wrapper.scrollWidth * my.pixelRatio + 'px',
            left: 0,
        });
    },

    // Create & append the wrapper element
    createWrapper: function (annotation_labels) {
        var my = this;
        annotation_labels.forEach(function (tagName, index) {
            // console.log($(".labels" + index)[0])
            my.container = $(".labels" + index)[0]

            my.wrapper = my.container.appendChild(
                document.createElement(tagName)
            );

            my.style(my.wrapper, {
                display: 'block',
                position: 'relative',
                height: my.height + 'px',
                "border-style": "solid",
                "border-width": "1px",
                "border-color": "black",
            });

            if (index != 0) {
                my.style(my.wrapper, {
                    "border-top": 0,
                })
            }

            if (my.wavesurfer.params.fillParent || my.wavesurfer.params.scrollParent) {
                my.style(my.wrapper, {
                    width: '100%',
                    overflow: 'hidden',
                });
            }

            my.labelsElement = my.wrapper.appendChild(document.createElement('div'));
            my.labelsElement.className = tagName
            my.style(my.labelsElement, {
                height: my.height + 'px',
                width: my.drawer.wrapper.scrollWidth * my.pixelRatio + 'px',
                left: 0,
            });


        })
        // this.container = null;
        // this.wrapper = null;
        // this.labelsElement = null;
    },

    // Remove the label container element
    clear: function () {
        if (this.labelsElement) {
            this.labelsElement.parentElement.removeChild(this.labelsElement);
            this.labelsElement = null;
        }
    },

    // Create and append the label container element
    render: function () {
        this.clear();

        this.labelsElement = this.wrapper.appendChild(document.createElement('div'));
        this.labelsElement.className = this.params.label_container

        this.style(this.labelsElement, {
            height: this.height + 'px',
            width: this.drawer.wrapper.scrollWidth * this.pixelRatio + 'px',
            left: 0,
        });


    },

    updateScroll: function () {
        this.wrapper.scrollLeft = this.drawer.wrapper.scrollLeft;
    },

    // Create & append a label element that is associated with the given region
    add: function (region) {
        var label = Object.create(WaveSurfer.Label);
        if (this.labelsElement !== null) {
            // console.log(this.labelsElement)
            label.init(region, this.labelsElement, this.index_color, this.color_pallet); //  $('.tv' )[0] Thisssssss is th one that determines where to show the label

        }

        this.labels[region.id] = label;

        region.on('remove', (function () {
            this.labels[region.id].remove();
            delete this.labels[region.id];
        }).bind(this));

        return label;
    },

    // Rearrange the labels to reduce overlap
    rearrange: function () {
        // First place all label elements in bottom row
        for (var id in this.labels) {
            // 2 px above wavesurfer canvas
            this.labels[id].row = 0;
        }

        this.assignRows();

        for (var id in this.labels) {
            this.labels[id].updateRender(2 + (this.rowHeight * (this.labels[id].row % this.maxRows)));
        }
    },

  
    assignRows: function () {
        for (var id in this.labels) {
            this.labels[id].row = 0;
        }

        for (var row = 0; row < (this.maxRows * 2); row++) {
            for (var id1 in this.labels) {


                var label = this.labels[id1];
                for (var id2 in this.labels) {
                    var otherLabel = this.labels[id2];
                    if ((otherLabel === label) || (otherLabel.row !== label.row)) {
                        continue;
                    }

                    if ((label.left() <= otherLabel.right() && label.left() >= otherLabel.left()) ||
                        (label.right() >= otherLabel.left() && label.right() <= otherLabel.right()) ||
                        (label.right() >= otherLabel.right() && label.left() <= otherLabel.left())) {
                        if (label.region.element.offsetWidth < otherLabel.region.element.offsetWidth) {
                            if (label.container === otherLabel.container) {
                                label.row += 1;
                            }

                        }
                    }
                }
            }
        }
    }
};


WaveSurfer.util.extend(WaveSurfer.Labels, WaveSurfer.Observer);

/**
 * Purpose:
 *   Individual label elements
 * Dependencies:
 *   WaveSurfer (lib/wavesurfer.min.js), WaveSurfer.Region (src/wavesurfer.regions.js), Font Awesome
 */
WaveSurfer.Label = {
    style: WaveSurfer.Drawer.style,

    init: function (region, container, index_color, color_pallet) {
        // console.log(container)
        this.container = container;
        this.wavesurfer = region.wavesurfer;
        this.element = null;
        this.playBtn = null;
        this.text = null;
        region.annotationLabel = this;
        region.annotation = this.container.className
        this.region = region;
        // this.colors = ['#ffa69e', '#faf3dd', '#b8f2e6', '#aed9e0', '#5e6472'];
        this.colors = color_pallet
        //['#3a86ff', '#ff006e', '#8338ec', '#fb5607', '#ffbe0b', '#06d6a0']
        this.region.color = this.colors[this.container.className]
        this.render();
        this.row = 0;
    },

    // Create and append individual label element
    render: function () {
        var labelEl = document.createElement('tag');
        this.element = this.container.appendChild(labelEl);

        this.style(this.element, {
            position: 'absolute',
            whiteSpace: 'nowrap',
            backgroundColor: '#7C7C7C',
            color: '#ffffff',
            padding: '0px 5px',
            borderRadius: '2px',
            // fontSize: '12px',
            textTransform: 'uppercase',
            textOverflow: 'ellipsis',
            overflow: 'hidden'
        });

        // Add play button inside the label
        this.playBtn = this.element.appendChild(document.createElement('i'));
        this.playBtn.className = 'fa fa-play-circle'; // Font Awesome Icon
        this.style(this.playBtn, {
            marginRight: '5px',
            cursor: 'pointer'
        });

        this.text = this.element.appendChild(document.createElement('span'));
        this.text.innerHTML = '?';

        // add delete region to the right
        this.deleteRegion = labelEl.appendChild(document.createElement('i'));
        this.deleteRegion.className = 'fa fa-times-circle';

        this.style(this.deleteRegion, {
            position: 'absolute',
            marginTop: '3px',
            right: '0px',
            marginRight: '5px',
            cursor: 'pointer'
        });

        // Place the label on the bottom row
        this.updateRender(2);
        this.bindEvents();
    },

    // Update the label element with it's corresponding region's annotation. Also update the label elements position.
    // The bottom parameter is how many pixels away from the label container's bottom the label element will be placed
    updateRender: function (bottom) {

        this.text.innerHTML = (this.region.annotation || '?');
        this.style(this.element, {
            left: this.region.element.offsetLeft + 'px',
            bottom: bottom + 'px',
            width: this.region.element.offsetWidth + 'px',
            backgroundColor: this.region.color,
            zIndex: this.wavesurfer.drawer.wrapper.scrollWidth - this.element.offsetWidth,
        });
    },

    left: function () {
        return this.element.offsetLeft;
    },

    right: function () {
        return this.element.offsetLeft + this.element.offsetWidth;
    },

    remove: function () {
        this.container.removeChild(this.element);
    },

    // Add event handlers for when the user clicks the labels play btn or double clicks the label
    bindEvents: function () {
        var my = this;
        // console.log(my)
        // If the user click the play button in the label, play the sound for the associated region
        this.playBtn.addEventListener('click', function (e) {
            my.region.play();
        });
        // If the user dbl clicks the label, trigger the dblclick event for the assiciated region
        this.element.addEventListener('click', function (e) {
            my.region.wavesurfer.fireEvent('label-click', my.region, e);
        });

        this.deleteRegion.addEventListener('click', function (e) {
            e.stopPropagation();
            my.region.remove();
        });
    }
};

WaveSurfer.util.extend(WaveSurfer.Label, WaveSurfer.Observer);
