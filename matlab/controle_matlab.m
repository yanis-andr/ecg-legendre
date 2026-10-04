% CONTROLE_MATLAB
% Rejoue la chaîne de classification_ecg.m (copie, dossier matlab_check/)
% et exporte de quoi la comparer à la version Python :
%   - les coefficients c_0..c_12 de tous les battements (même boucle que classification_ecg.m) ;
%   - pour plusieurs graines : la sélection équilibrée, le découpage 80/20,
%     l'exactitude KNN (K=1 et meilleur K) et SVM RBF.
% Lancement : matlab -batch "addpath('../matlab'); controle_matlab" depuis matlab_check/

Nmax = 12; WIN_HALF = 90;
PATIENTS = {'100', '101', '105', '111'};
win_len = 2*WIN_HALF + 1;
x_win = linspace(-1, 1, win_len);

feat = []; lab = []; pat = []; pos = [];
for p = 1:numel(PATIENTS)
    D = load(sprintf('patient_%s.mat', PATIENTS{p}));
    sig = double(D.signal);
    r_peaks = double(D.r_peaks) + 1;          % comme classification_ecg.m
    lbl = double(D.labels_num);
    for k = 1:numel(r_peaks)
        if lbl(k) == 3, continue; end
        i1 = r_peaks(k) - WIN_HALF; i2 = r_peaks(k) + WIN_HALF;
        if i1 < 1 || i2 > numel(sig), continue; end
        w = sig(i1:i2);
        if max(w) - min(w) < 1e-10, continue; end
        w = 2*(w - min(w))/(max(w) - min(w)) - 1;
        ck = zeros(1, Nmax+1);
        for n = 0:Nmax
            Pn = Legendre(x_win, n);
            ck(n+1) = trapz(x_win, w(:)' .* Pn) / trapz(x_win, Pn .* Pn);
        end
        feat = [feat; ck]; lab = [lab; lbl(k)];
        pat = [pat; str2double(PATIENTS{p})]; pos = [pos; double(D.r_peaks(k))];
    end
end

seeds = [42, 1:20];
K_vals = [1, 3, 5, 7, 11];
acc_knn1 = zeros(size(seeds)); acc_knnbest = acc_knn1; acc_svm = acc_knn1;
splits = cell(size(seeds));
for s = 1:numel(seeds)
    rng(seeds(s));
    idx_N = find(lab == 0); idx_A = find(lab == 1);
    n_each = min(numel(idx_N), numel(idx_A));
    sel = [idx_N(randperm(numel(idx_N), n_each)); idx_A(randperm(numel(idx_A), n_each))];
    X = feat(sel, :); y = lab(sel);
    perm = randperm(numel(y)); n_tr = round(0.8*numel(y));
    tr = perm(1:n_tr); te = perm(n_tr+1:end);
    accs = zeros(size(K_vals));
    for ki = 1:numel(K_vals)
        m = fitcknn(X(tr,:), y(tr), 'NumNeighbors', K_vals(ki), 'Standardize', true);
        accs(ki) = mean(predict(m, X(te,:)) == y(te)) * 100;
    end
    acc_knn1(s) = accs(1); acc_knnbest(s) = max(accs);
    m = fitcsvm(X(tr,:), y(tr), 'KernelFunction', 'rbf', 'Standardize', true, ...
                'BoxConstraint', 1.0, 'KernelScale', 'auto');
    acc_svm(s) = mean(predict(m, X(te,:)) == y(te)) * 100;
    splits{s} = struct('sel', sel, 'train', sel(tr), 'test', sel(te));
    fprintf('graine %2d : KNN1 %.2f  KNNbest %.2f  SVM %.2f\n', seeds(s), ...
            acc_knn1(s), acc_knnbest(s), acc_svm(s));
end

save('matlab_resultats.mat', 'feat', 'lab', 'pat', 'pos', 'seeds', ...
     'acc_knn1', 'acc_knnbest', 'acc_svm', 'splits', '-v7');
fprintf('OK\n');
