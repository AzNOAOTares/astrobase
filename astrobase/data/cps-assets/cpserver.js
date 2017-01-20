// cpserver.js - Waqas Bhatti (wbhatti@astro.princeton.edu) - Jan 2017
// License: MIT. See LICENSE for the full text.
//
// This contains the JS to drive the checkplotserver's interface.
//

//////////////
// JS BELOW //
//////////////

// this contains utility functions
var cputils = {

    // this encodes a string to base64
    // https://developer.mozilla.org/en-US/docs/Web/API/WindowBase64/Base64_encoding_and_decoding
    b64_encode: function (str) {
        return btoa(
            encodeURIComponent(str)
                .replace(/%([0-9A-F]{2})/g,
                         function(match, p1) {
                             return String.fromCharCode('0x' + p1);
                         }));
    },

    // this turns a base64 string into an image by updating its source
    b64_to_image: function (str, targetelem) {

        var datauri = 'data:image/png;base64,' + str;
        $(targetelem).attr('src',datauri);

    }

};


// this contains updates to current checkplots
var cptracker = {

    // this is the actual object that will get written to JSON or CSV we'll
    // search for the latest update and write that to disk if told to do so. if
    // we're told to include all updates, then we'll get all the history for
    // each checkplot
    cpdata: {},

    // this generates a CSV for download
    // FIXME: figure out how to do this
    cpdata_to_csv: function () {

    },

    // this generates a JSON for download
    cpdata_to_json: function () {

    }

};


// this is the container for the main functions
var cpv = {
    // these hold the current checkplot's data and filename respectively
    currfind: 0,
    currfile: '',
    currcp: {},

    // this function generates a spinner
    make_spinner: function (spinnermsg) {

        var spinner =
            '<div class="spinner">' +
            spinnermsg +
            '<div class="rect1"></div>' +
            '<div class="rect2"></div>' +
            '<div class="rect3"></div>' +
            '<div class="rect4"></div>' +
            '<div class="rect5"></div>' +
            '</div>';

        $('#alert-box').html(spinner);

    },

    // this function generates an alert box
    make_alert: function (alertmsg) {

        var xalert =
            '<div class="alert alert-warning alert-dismissible fade show" ' +
            'role="alert">' +
            '<button type="button" class="close" data-dismiss="alert" ' +
            'aria-label="Close">' +
            '<span aria-hidden="true">&times;</span>' +
            '</button>' +
            alertmsg +
            '</div>';

        $('#alert-box').html(xalert);

    },

    // this loads a checkplot from an image file into an HTML canvas object
    load_checkplot: function (filename) {

        console.log('loading ' + filename);

        // start the spinny thing
        cpv.make_spinner('loading...');

        // build the title for this current file
        var plottitle = $('#checkplot-current');
        var filelink = filename;
        var objectidelem = $('#objectid');
        var twomassidelem = $('#twomassid');

        plottitle.html(filelink);

        if (cpv.currfile.length > 0) {
            // un-highlight the previous file in side bar
            $("a[data-fname='" + cpv.currfile + "']").unwrap();
        }

        // do the AJAX call to get this checkplot
        var ajaxurl = '/cp/' + cputils.b64_encode(filename);

        $.getJSON(ajaxurl, function (data) {

            cpv.currcp = data.result;
            console.log('received cp for ' + cpv.currcp.objectid);

            /////////////////////////////////////////////////
            // update the UI with elems for this checkplot //
            /////////////////////////////////////////////////


            // update the objectid header
            objectidelem.html(cpv.currcp.objectid);
            // update the twomassid header
            twomassidelem.html('2MASS J' + cpv.currcp.objectinfo.twomassid);

            // update the finder chart
            cputils.b64_to_image(cpv.currcp.finderchart,
                                 '#finderchart');

            // update the objectinfo
            var hatinfo = '<strong>' +
                (cpv.currcp.objectinfo.stations.split(',')).join(', ') +
                '</strong><br>' +
                '<strong>LC points:</strong> ' +
                cpv.currcp.objectinfo.ndet;
            $('#hatinfo').html(hatinfo);

            var coordspm =
                '<strong>RA, Dec:</strong> ' +
                '<a title="SIMBAD search at these coordinates" ' +
                'href="http://simbad.u-strasbg.fr/simbad/sim-coo?Coord=' +
                cpv.currcp.objectinfo.ra + '+' + cpv.currcp.objectinfo.decl +
                '&Radius=1&Radius.unit=arcmin' +
                '" rel="nofollow" target="_blank">' +
                math.format(cpv.currcp.objectinfo.ra,6) + ', ' +
                math.format(cpv.currcp.objectinfo.decl,6) + '</a><br>' +
                '<strong>Total PM:</strong> ' +
                math.format(cpv.currcp.objectinfo.propermotion,5) +
                ' mas/yr<br>' +
                '<strong>Reduced PM:</strong> ' +
                math.format(cpv.currcp.objectinfo.reducedpropermotion,4);
            $('#coordspm').html(coordspm);

            var mags = '<strong><em>gri</em>:</strong> ' +
                math.format(cpv.currcp.objectinfo.sdssg,5) + ', ' +
                math.format(cpv.currcp.objectinfo.sdssr,5) + ', ' +
                math.format(cpv.currcp.objectinfo.sdssi,5) + '<br>' +
                '<strong><em>JHK</em>:</strong> ' +
                math.format(cpv.currcp.objectinfo.jmag,5) + ', ' +
                math.format(cpv.currcp.objectinfo.hmag,5) + ', ' +
                math.format(cpv.currcp.objectinfo.kmag,5) + '<br>' +
                '<strong><em>BV</em>:</strong> ' +
                math.format(cpv.currcp.objectinfo.bmag,5) + ', ' +
                math.format(cpv.currcp.objectinfo.vmag,5);
            $('#mags').html(mags);

            var colors = '<strong><em>B - V</em>:</strong> ' +
                math.format(cpv.currcp.objectinfo.bvcolor,4) + '<br>' +
                '<strong><em>i - J</em>:</strong> ' +
                math.format(cpv.currcp.objectinfo.ijcolor,4) + '<br>' +
                '<strong><em>J - K</em>:</strong> ' +
                math.format(cpv.currcp.objectinfo.jkcolor,4);
            $('#colors').html(colors);

            // update the magseries plot
            cputils.b64_to_image(cpv.currcp.magseries,
                                '#magseriesplot');

            // update the varinfo
            if (cpv.currcp.varinfo.objectisvar == true) {

                console.log('objectisvar = true');
                $('#varcheck-yes').click();

            }
            else if (cpv.currcp.varinfo.objectisvar == false) {

                console.log('objectisvar = false');
                $('#varcheck-no').click();

            }
            else {

                console.log('objectisvar = maybe (null)');
                $('#varcheck-maybe').click();

            }
            $('#objectperiod').val(cpv.currcp.varinfo.varperiod);
            $('#objectepoch').val(cpv.currcp.varinfo.varepoch);
            $('#objecttags').val(cpv.currcp.objectinfo.objecttags);
            $('#objectcomments').val(cpv.currcp.objectcomments);
            $('#vartags').val(cpv.currcp.varinfo.vartags);

            // update the phased light curves

            // first, count the number of methods we have in the cp
            var lspmethods = [];
            var ncols = 0;

            if ('pdm' in cpv.currcp) {
                lspmethods.push('pdm');
                ncols = ncols + 1;
            }
            if ('gls' in cpv.currcp) {
                lspmethods.push('gls');
                ncols = ncols + 1;
            }
            if ('bls' in cpv.currcp) {
                lspmethods.push('bls');
                ncols = ncols + 1;
            }
            if ('aov' in cpv.currcp) {
                lspmethods.push('aov');
                ncols = ncols + 1;
            }

            var colwidth = 12/ncols;

            // zero out previous stuff
            $('.phased-container').empty();

            // then go through each lsp method, and generate the containers
            for (let lspmethod of lspmethods) {

                if (lspmethod in cpv.currcp) {

                    var nbestperiods = cpv.currcp[lspmethod].nbestperiods;
                    var periodogram = cpv.currcp[lspmethod].periodogram;

                    // start putting together the container for this method
                    var mcontainer_coltop =
                        '<div class="col-sm-' + colwidth +
                        '" "data-lspmethod="' + lspmethod + '">';
                    var mcontainer_colbot = '</div>';

                    var periodogram_row =
                        '<div class="row periodogram-container">' +
                        '<div class="col-sm-12">' +
                        '<img src="data:image/png;base64,' +
                        cpv.currcp[lspmethod].periodogram + '" ' +
                        'class="img-fluid" id="periodogram-' +
                        lspmethod + '">' + '</div></div>';

                    var phasedlcrows= [];

                    // up to 5 periods are possible
                    var periodindexes = ['phasedlc0',
                                         'phasedlc1',
                                         'phasedlc2',
                                         'phasedlc3',
                                         'phasedlc4'];

                    for (let periodind of periodindexes) {

                        if (periodind in cpv.currcp[lspmethod]) {

                            var phasedlcrow =
                                '<a href="#" class="phasedlc-select" ' +
                                'title="use this period and epoch" ' +
                                'data-lspmethod="' + lspmethod + '" ' +
                                'data-periodind="' + periodind + '" ' +
                                'data-currentbest="no" ' +
                                'data-period="' +
                                cpv.currcp[lspmethod][periodind].period + '" ' +
                                'data-epoch="' +
                                cpv.currcp[lspmethod][periodind].epoch + '">' +
                                '<div class="row py-1 phasedlc-container-row" ' +
                                'data-periodind="' + periodind + '">' +
                                '<div class="col-sm-12">' +
                                '<img src="data:image/png;base64,' +
                                cpv.currcp[lspmethod][periodind].plot + '"' +
                                'class="img-fluid" id="plot-' +
                                periodind + '">' + '</div></div></a>';
                            phasedlcrows.push(phasedlcrow);

                        }

                    }

                    // now that we've collected everything, generate the
                    // container column
                    var mcontainer = mcontainer_coltop + periodogram_row +
                        phasedlcrows.join(' ') + mcontainer_colbot;

                    // write the column to the phasedlc-container
                    $('.phased-container').append(mcontainer);

                }

            }


        }).done(function () {

            console.log('done with cp');

            // update the current file trackers
            cpv.currfile = filename;
            cpv.currind = parseInt(
                $("a[data-fname='" + filename + "']").attr('data-findex')
            );

            // highlight the file in the sidebar list
            $("a[data-fname='" + filename + "']").wrap('<strong></strong>')

            // fix the height of the sidebar as required
            var winheight = $(window).height();
            var docheight = $(document).height();
            var ctrlheight = $('.sidebar-controls').height()

            $('.sidebar').css({'height': docheight + 'px'});

            // get rid of the spinny thing
            $('#alert-box').empty();

        }).fail (function (xhr) {

            cpv.make_alert('could not load checkplot <strong>' +
                           filename + '</strong>!');
            console.log('cp loading failed from ' + ajaxurl);

        });


    },

    // this functions saves the current checkplot by doing a POST request to the
    // backend. this MUST be called on every checkplot list action (i.e. next,
    // prev, before load of a new checkplot, so changes are always saved). UI
    // elements in the checkplot list will tag the saved checkplots
    // appropriately
    save_checkplot: function (nextfunc_callback, nextfunc_arg) {

        // do the AJAX call to get this checkplot
        var ajaxurl = '/cp/' + cputils.b64_encode(cpv.currfile);

        // make sure that we've saved the input varinfo, objectinfo and comments
        cpv.currcp.varinfo.vartags = $('#vartags').val();
        cpv.currcp.objectinfo.objecttags = $('#objecttags').val();
        cpv.currcp.objectcomments = $('#objectcomments').val();

        var cppayload = JSON.stringify({objectid: cpv.currcp.objectid,
                                        objectinfo: cpv.currcp.objectinfo,
                                        varinfo: cpv.currcp.varinfo,
                                        comments: cpv.currcp.objectcomments});

        // first, generate the object to send with the POST request
        var postobj = {cpfile: cpv.currfile,
                       cpcontents: cppayload};

        // this is to deal with UI elements later
        var currfile = postobj.cpfile;

        // next, do a saving animation in the alert box
        cpv.make_spinner('saving...');

        // next, send the POST request and handle anything the server returns
        // FIXME: this should use _xsrf once we set that up
        $.post(ajaxurl, postobj, function (data) {

            // get the info from the backend
            var updatestatus = data.status;
            var updatemsg = data.message;
            var updateinfo = data.result;

            // update the cptracker with what changed so we can try to undo
            // later if necessary.
            if (updatestatus == 'ok') {

                // we don't need full precision for the time of update
                var updts = parseInt(updateinfo.unixtime);

                if (!(cpfile in cptracker.cpdata)) {
                    cptracker.cpdata[cpfile] = {};
                }

                cptracker.cpdata.cpfile[updts] = {
                    changes: updateinfo.changes,
                    filename: updateinfo.checkplot,
                    unixtime: updateinfo.unixtime
                };

            }

            else {
                cpv.make_alert(updatemsg);
            }

        // on POST done, update the UI elements in the checkplot list
        // and call the next function.
        },'json').done(function (xhr) {

            // clean out the alert box
            $('#alert-box').empty();

            // tag the current checkplot in the list as done

            // clean out the cpv.currcp and cpv.currfile before the next one
            // loads

            // call the next function. we call this here so we can be sure the
            // save finished before the next action starts
            if (!(nextfunc_callback === undefined)) {
                nextfunc_callback(nextfunc_arg);
            }

        // if POST failed, pop up an alert in the alert box
        }).fail(function (xhr) {

            var errmsg = 'could not update ' +
                currfile + ' because of an internal server error';
            cpv.make_alert(errmsg);

        });

    },


    // this binds actions to the web-app controls
    action_setup: function () {

        // the previous checkplot link
        $('.checkplot-prev').on('click',function (evt) {

            evt.preventDefault();

            // find the current index
            var prevfile = $("a[data-findex='" + (cpv.currentfind-1) + "']")
                .attr('data-fname');
            console.log('moving to prev file: ' + prevfile);
            if (prevfile != undefined) {
                cpv.load_checkplot(prevfile);
            }
            else {
                console.log('no prev file, staying right here');
            }

        });

        // the next checkplot link
        $('.checkplot-next').on('click',function (evt) {

            evt.preventDefault();

            // find the current index
            var nextfile = $("a[data-findex='" + (cpv.currentfind+1) + "']")
                .attr('data-fname');
            console.log('moving to next file: ' + nextfile);

            if (nextfile != undefined) {
                cpv.load_checkplot(nextfile);
            }
            else {
                console.log('no next file, staying right here');
            }

        });

        // clicking on a checkplot file in the sidebar
        $('#checkplotlist').on('click', '.checkplot-load', function (evt) {

            evt.preventDefault();

            var filetoload = $(this).attr('data-fname');
            console.log('file to load: ' + filetoload);

            // save the currentcp if one exists, use the load_checkplot as a
            // callback to load the next one
            if (('objectid' in cpv.currcp) && (cpv.currfile.length > 0))  {
                cpv.save_checkplot(cpv.load_checkplot,filetoload);
            }

            else {
                // ask the backend for this file
                cpv.load_checkplot(filetoload);
            }

        });

        // clicking on a phased LC loads its period and epoch into the boxes
        // also saves them to the currcp
        $('.phased-container').on('click','.phasedlc-select', function (evt) {

            evt.preventDefault();

            var period = $(this).attr('data-period');
            var epoch = $(this).attr('data-epoch');

            console.log('period selected = ' + period);
            console.log('epoch selected = ' + epoch);

            // update the boxes
            $('#objectperiod').val(period);
            $('#objectepoch').val(epoch);

            // save to currcp
            cpv.currcp.varinfo.varperiod = parseFloat(period);
            cpv.currcp.varinfo.varepoch = parseFloat(epoch);

            // add a selected class
            var selector = '[data-periodind="' +
                $(this).attr('data-periodind') +
                '"]';
            $('.phasedlc-container-row').removeClass('phasedlc-selected');
            $(this)
                .children('.phasedlc-container-row')
                .filter(selector).addClass('phasedlc-selected');

        });

        // clicking on the is-object-variable control saves the info to currcp
        $("input[name='varcheck']").on('click', function (evt) {

            var yes = $('#varcheck-yes').prop('checked');
            var no = $('#varcheck-no').prop('checked');
            var maybe = $('#varcheck-maybe').prop('checked');

            if (yes) {
                cpv.currcp.varinfo.objectisvar = true;
            }
            else if (no) {
                cpv.currcp.varinfo.objectisvar = false;
            }
            else if (maybe) {
                cpv.currcp.varinfo.objectisvar = null;
            }

            console.log('yes, no, maybe ' + yes + ',' + no + ',' + maybe);

        });


        // resizing the window fixes the sidebar again
        $(window).on('resize', function (evt) {

            // fix the height of the sidebar as required
            var winheight = $(window).height();
            var docheight = $(document).height();
            var ctrlheight = $('.sidebar-controls').height()

            $('.sidebar').css({'height': docheight + 'px'});

        });


    }

};