/*
    Proof of concept robohash in JavaScript.
    Needs refactoring.

    Output matches minihash.py, not original algorithm.
 */

// Prng looks weird, but it matches the one in Python.
function SimplePRNG(input, key){
    if(!key){
        key = "";
    }
    var keyBits = sjcl.codec.utf8String.toBits(key),
        inBits = sjcl.codec.utf8String.toBits(input),
        hm = new sjcl.misc.hmac(keyBits, sjcl.hash.sha512),
        state,
        chunk = 0;  // just good for 8 calls right now.

    hm.update(inBits);
    state = hm.digest();

    this.nxtMod = function(mod){
        var slice, res;
        if (chunk == 8){
            throw "blahblah. todo: continue hashing stuff..."
        }
        slice = sjcl.bitArray.bitSlice(state, 64*chunk, 64*(chunk+1));
        chunk += 1;
        res = sjcl.bn.fromBits(slice).mod(mod).toBits();
        return sjcl.codec.bytes.fromBits(res)[0];
    }
}

function weirdSort(x,y){ // ugh; fixme.
    return x.split('#')[1] > y.split('#')[1];
}

function pickParts(prng){
    var colors = Object.keys(set1tree).sort(),
        color = colors[prng.nxtMod(colors.length)],
        set = set1tree[color];

    var types = Object.keys(set).sort(weirdSort),
        type;
    
    var files = types.map(function(partSetName){
        var partSet = set[partSetName],
            part = partSet[prng.nxtMod(partSet.length)];
        return color + "/" + encodeURIComponent(partSetName) + "/" + encodeURIComponent(part);
        
    });
    return files;
}

function loadPartFiles(files, onDone){
    var left = files.length,
        partBin = {};

    function done(){
        left -= 1;
        if(left == 0){
            onDone(partBin);
        }
    }
    files.forEach(function(file){
        var url = baseUrl + file,
            img = new Image();
        img.onload = done;
        img.src = url;
        partBin[file] = img;
    });
}

function assembleParts(partBin){
    var canvas = document.querySelector('#rhc'),
        ctx = canvas.getContext("2d");
    files.forEach(function(file){
        var img = partBin[file];
        ctx.drawImage(img, 0, 0);
    });
}