(function() {
    let detailsState = new Map();
    function beforePrint() {
        const allDetails = document.querySelectorAll('details');
        allDetails.forEach(details => {
        detailsState.set(details, details.open);
        if (!details.open) {
            details.open = true;
        }
        });
    }
    function afterPrint() {
        for (let [details, wasOpen] of detailsState.entries()) {
        if (!wasOpen) {
            details.open = false;
        }
        }
        detailsState.clear();
    }
    if (window.matchMedia) {
        const mediaQueryList = window.matchMedia('print');
        window.addEventListener('beforeprint', beforePrint);
        window.addEventListener('afterprint', afterPrint);
        mediaQueryList.addListener(mql => {
        if (mql.matches) {
            beforePrint();
        } else {
            afterPrint();
        }
        });
    } else {
        window.addEventListener('beforeprint', beforePrint);
        window.addEventListener('afterprint', afterPrint);
    }
})();