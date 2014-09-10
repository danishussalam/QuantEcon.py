r"""
======================
The Solow Growth Model
======================

The following summary of the [solow1956] model of economic growth largely
follows [romer2011].

Assumptions
===========

The production function
----------------------------------------------

The [solow1956] model of economic growth focuses on the behavior of four
variables: output, `Y`, capital, `K`, labor, `L`, and knowledge (or technology
or the ``effectiveness of labor''), `A`. At each point in time the economy has
some amounts of capital, labor, and knowledge that can be combined to produce
output according to some production function, `F`.

.. math::

    Y(t) = F(K(t), A(t)L(t))

where `t` denotes time.

The evolution of the inputs to production
-----------------------------------------
The initial levels of capital, :math:`K_0`, labor, :math:`L_0`, and technology,
:math:`A_0`, are taken as given. Labor and technology are assumed to grow at
constant rates:

.. math::

    \dot{A}(t) = gA(t)
    \dot{L}(t) = nL(t)

where the rate of technological progrss, `g`, and the population growth rate,
`n`, are exogenous parameters.

Output is divided between consumption and investment. The fraction of output
devoted to investment, :math:`0 < s < 1`, is exogenous and constant. One unit
of output devoted to investment yields one unit of new capital. Capital is
assumed to decpreciate at a rate :math:`0\le \delta`. Thus aggregate capital
stock evolves according to

.. math::

    \dot{K}(t) = sY(t) - \delta K(t).

Although no restrictions are placed on the rates of technological progress and
population growth, the sum of `g`, `n`, and :math:`delta` is assumed to be
positive.

The dynamics of the model
=========================

Because the economy is growing over time (due to exogenous technological
progress and population growth) it is useful to focus on the behavior of
capital stock per unit of effective labor, :math:`k\equiv K/AL`. Applying
the chain rule to the equation of motion for capital stock yields (after a
bit of algebra!) an equation of motion for capital stock per unit of effective
labor.

.. math::

    \dot{k}(t) = s f(k) - (g + n + \delta)k(t)

References
==========
.. [romer2011] D. Romer. *Advanced Macroeconomics, 4th edition*, MacGraw Hill, 2011.
.. [solow1956] R. Solow. *A contribution to the theory of economic growth*, Quarterly Journal of Economics, 70(1):64-95, 1956.

@author : David R. Pugh
@date : 2014-08-18

TODO:
5. Finish section on solving Solow model in demo notebook.
6. Write code for computing impulse response functions.
7. Write code for plotting impulse response functions.
8. Finish section on calibrating the Solow model in the demo notebook.
9. Finish writing docs (include some basic usage examples in the module docs).

"""
import matplotlib.pyplot as plt
import numpy as np
from scipy import optimize
import sympy as sym

from ... import ivp


# declare key variables for the model
t, X = sym.var('t'), sym.DeferredVector('X')
A, k, K, L = sym.var('A, k, K, L')

# declare required model parameters
g, n, s, delta = sym.var('g, n, s, delta')


class Model(object):

    def __init__(self, output, params):
        """
        Create an instance of the Solow growth model.

        Parameters
        ----------
        output : sym.Basic
            Symbolic expression defining the aggregate production function.
        params : dict
            Dictionary of model parameters.

        """
        # cached values
        self.__intensive_output = None
        self.__mpk = None
        self.__numeric_system = None
        self.__numeric_jacobian = None

        self.output = output
        self.params = params

    @property
    def _intensive_output(self):
        """
        :getter: Return vectorized symbolic intensive aggregate production.
        :type: function

        """
        if self.__intensive_output is None:
            args = [k] + sym.var(list(self.params.keys()))
            self.__intensive_output = sym.lambdify(args, self.intensive_output,
                                                   modules=[{'ImmutableMatrix': np.array}, "numpy"])
        return self.__intensive_output

    @property
    def _mpk(self):
        """
        :getter: Return vectorized symbolic marginal product capital.
        :type: function

        """
        if self.__mpk is None:
            args = [k] + sym.var(list(self.params.keys()))
            self.__mpk = sym.lambdify(args, self.marginal_product_capital,
                                      modules=[{'ImmutableMatrix': np.array}, "numpy"])
        return self.__mpk

    @property
    def _numeric_system(self):
        """
        Vectorized, numpy-aware function defining the system of ODEs.

        :getter: Return vectorized symbolic system of ODEs.
        :type: function

        """
        if self.__numeric_system is None:
            self.__numeric_system = sym.lambdify(self._symbolic_args,
                                                 self._symbolic_system,
                                                 modules=[{'ImmutableMatrix': np.array}, "numpy"])
        return self.__numeric_system

    @property
    def _numeric_jacobian(self):
        """
        Vectorized, numpy-aware function defining the Jacobian matrix of
        partial derivatives.

        :getter: Return vectorized Jacobian matrix of partial derivatives.
        :type: function

        """
        if self.__numeric_jacobian is None:
            self.__numeric_jacobian = sym.lambdify(self._symbolic_args,
                                                   self._symbolic_jacobian,
                                                   modules=[{'ImmutableMatrix': np.array}, "numpy"])
        return self.__numeric_jacobian

    @property
    def _symbolic_args(self):
        """
        List of symbolic arguments used in constructing vectorized versions of
        _symbolic_system and _symbolic_jacobian.

        :getter: Return list of symbolic arguments.
        :type: list

        """
        args = [t, X] + sym.var(self.params.keys())
        return args

    @property
    def _symbolic_system(self):
        """
        Symbolic matrix defining the system of ODEs.

        :getter: Return the matrix defining the system of ODEs.
        :type: sym.MutableDenseMatrix

        """
        change_of_vars = {k: X[0]}
        return sym.Matrix([self.k_dot]).subs(change_of_vars)

    @property
    def _symbolic_jacobian(self):
        """
        Symbolic Jacobian matrix for the system of ODEs.

        :getter: Return the symbolic Jacobian matrix.
        :type: sym.MutableDenseMatrix

        """
        N = self._symbolic_system.shape[0]
        return self._symbolic_system.jacobian([X[i] for i in range(N)])

    @property
    def effective_depreciation_rate(self):
        """
        Effective depreciation rate for capital stock (per unit effective labor).

        :getter: Return the current effective depreciation rate.
        :type: float

        Notes
        -----
        The effective depreciation rate of physical capital takes into account
        both technological progress and population growth, as well as physical
        depreciation.

        """
        return sum(self.params[key] for key in ['g', 'n', 'delta'])

    @property
    def intensive_output(self):
        r"""
        Symbolic expression for the intensive form of aggregate production.

        :getter: Return the current intensive production function.
        :type: sym.Basic

        Notes
        -----
        The assumption of constant returns to scale allows us to work the the
        intensive form of the aggregate production function, `F`. Defining
        :math:`c=1/AL` one can write

        ..math::

            F\bigg(\frac{K}{AL}, 1\bigg) = \frac{1}{AL}F(A, K, L)

        Defining :math:`k=K/AL` and :math:`y=Y/AL` to be capital per unit
        effective labor and output per unit effective labor, respectively, the
        intensive form of the production function can be written as

        .. math::

            y = f(k).

        Additional assumptions are that `f` satisfies :math:`f(0)=0`, is
        concave (i.e., :math:`f'(k) > 0, f''(k) < 0`), and satisfies the Inada
        conditions:

        .. math::
            :type: eqnarray

            \lim_{k \rightarrow 0} &=& \infty \\
            \lim_{k \rightarrow \infty} &=& 0

        The [inada1964]_ conditions are sufficient (but not necessary!) to
        ensure that the time path of capital per effective worker does not
        explode.

        .. [inada1964] K. Inda. *Some structural characteristics of Turnpike Theorems*, Review of Economic Studies, 31(1):43-58, 1964.

        """
        return self.output.subs({'A': 1.0, 'K': k, 'L': 1.0})

    @property
    def ivp(self):
        r"""
        Initial value problem

        :getter: Return an instance of the ivp.IVP class representing the Solow
        model.
        :type: ivp.IVP

        Notes
        -----
        The Solow model with can be formulated as an initial value problem
        (IVP) as follows.

        .. math::

            \dot{k}(t) = sf(k(t)) - (g + n + \delta)k(t),\ t\ge t_0,\ k(t_0) = k_0

        The solution to this IVP is a function :math:`k(t)` describing the time
        path of capital stock (per unit effective labor).

        """
        tmp_ivp = ivp.IVP(self._numeric_system, self._numeric_jacobian)
        tmp_ivp.f_params = tuple(self.params.values())
        tmp_ivp.jac_params = tuple(self.params.values())
        return tmp_ivp

    @property
    def k_dot(self):
        r"""
        Symbolic expression for the equation of motion for capital (per unit
        effective labor).

        :getter: Return the current equation of motion for capital (per unit
        effective labor).
        :type: sym.Basic

        Notes
        -----
        Because the economy is growing over time due to technological progress,
        `g`, and population growth, `n`, it makes sense to focus on the capital
        stock per unit effective labor, `k`, rather than aggregate physical
        capital, `K`. Since, by definition, :math:`k=K/AL`, we can apply the
        chain rule to the time derative of `k`.

        .. math::
            :type: eqnarray

            \dot{k}(t) &=& \frac{\dot{K}(t)}{A(t)L(t)} - \frac{K(t)}{[A(t)L(t)]^2}\bigg[\dot{A}(t)L(t) + \dot{L}(t)A(t)\bigg] \\
            &=& \frac{\dot{K}(t)}{A(t)L(t)} - \bigg(\frac{\dot{A}(t)}{A(t)} + \dot{L}(t)}{L(t)}\bigg)\frac{K(t)}{A(t)L(t)}

        By definition, math:`k=K/AL`, and by assumption :math:`\dot{A}/A` and
        :math:`\dot{L}/L` are `g` and `n` respectively. Aggregate capital stock
        evolves according to

        .. math::

            \dot{K}(t) = sF(K(t), A(t)L(t)) - \delta K(t).

        Substituting these facts into the above equation yields the equation of
        motion for capital stock (per unit effective labor).

        .. math::

            :type: eqnarray

            \dot{k}(t) &=& \frac{sF(K(t), A(t)L(t)) - \delta K(t)}{A(t)L(t)} - (g + n)k(t) \\
            &=& \frac{sY(t)}{A(t)L(t)} - (g + n + \delta)k(t) \\
            &=& sf(k(t)) - (g + n + \delta)k(t)

        """
        return s * self.intensive_output - (g + n + delta) * k

    @property
    def marginal_product_capital(self):
        r"""
        Symbolic expression for the marginal product of capital (per unit
        effective labor).

        :getter: Return the current marginal product of capital (per unit
        effective labor).
        :type: sym.Basic

        Notes
        -----
        The marginal product of capital is defined as follows:

        .. math::

            \frac{\partial F(K, AL)}{\partial K} \equiv f'(k)

        where :math:`k=K/AL` is capital stock (per unit effective labor).

        """
        return sym.diff(self.intensive_output, k)

    @property
    def output(self):
        r"""
        Symbolic expression for the aggregate production function.

        :getter: Return the current aggregate production function.
        :setter: Set a new aggregate production function
        :type: sym.Basic

        Notes
        -----
        At each point in time the economy has some amounts of capital, `K`,
        labor, `L`, and knowledge (or technology), `A`, that can be combined to
        produce output, `Y`, according to some function, `F`.

        .. math::

            Y(t) = F(K(t), A(t)L(t))

        where `t` denotes time. Note that `A` and `L` are assumed to enter
        multiplicatively. Typically `A(t)L(t)` denotes "effective labor", and
        technology that enters in this fashion is known as labor-augmenting or
        "Harrod neutral."

        A key assumption of the model is that the function `F` exhibits
        constant returns to scale in capital and labor inputs. Specifically,

        .. math::

            F(cK(t), cA(t)L(t)) = cF(K(t), A(t)L(t)) = cY(t)

        for any :math:`c \ge 0`.

        """
        return self._output

    @property
    def params(self):
        """
        Dictionary of model parameters.

        :getter: Return the current dictionary of model parameters.
        :setter: Set a new dictionary of model parameters.
        :type: dict

        Notes
        -----
        The following parameters are required:

        g : float
            Growth rate of technology.
        n : float
            Growth rate of the labor force.
        s : float
            Savings rate. Must satisfy `0 < s < 1`.
        delta : float
            Depreciation rate of physical capital. Must satisfy
            :math:`0 < \delta`.

        Although no restrictions are placed on the rates of technological
        progress and population growth, the sum of `g`, `n`, and :math:`delta`
        is assumed to be positive. The user mus also specify any additional
        model parameters specific to the chosen aggregate production function.

        """
        return self._params

    @output.setter
    def output(self, value):
        """Set a new production function."""
        self._output = self._validate_output(value)

        # clear the cache
        self.__intensive_output = None
        self.__mpk = None
        self.__numeric_system = None
        self.__numeric_jacobian = None

    @params.setter
    def params(self, value):
        """Set a new parameter dictionary."""
        self._params = self._validate_params(value)

    def _validate_output(self, output):
        """Validate the production function."""
        if not isinstance(output, sym.Basic):
            mesg = ("Output must be an instance of {}.".format(sym.Basic))
            raise AttributeError(mesg)
        if not ({A, K, L} < output.atoms()):
            mesg = ("Output must be an expression of technology, 'A', " +
                    "capital, 'K', and labor, 'L'.")
            raise AttributeError(mesg)
        else:
            return output

    def _validate_params(self, params):
        """Validate the model parameters."""
        if not isinstance(params, dict):
            mesg = "SolowModel.params must be a dict, not a {}."
            raise AttributeError(mesg.format(params.__class__))
        if params['s'] <= 0.0 or params['s'] >= 1.0:
            raise AttributeError('Savings rate must be in (0, 1).')
        if params['delta'] <= 0.0 or params['delta'] >= 1.0:
            raise AttributeError('Depreciation rate must be in (0, 1).')
        if params['g'] + params['n'] + params['delta'] <= 0.0:
            raise AttributeError("Sum of g, n, and delta must be positive.")
        else:
            return params

    def calibrate_model(self, *args, **kwargs):
        """Calibrate the model using some data."""
        raise NotImplementedError

    def compute_actual_investment(self, k):
        """
        Return the amount of output (per unit of effective labor) invested in
        the production of new capital.

        Parameters
        ----------
        k : array_like (float)
            Capital stock (per unit of effective labor)

        Returns
        -------
        actual_inv : array_like (float)
            Investment (per unit of effective labor)

        """
        actual_inv = self.params['s'] * self.compute_intensive_output(k)
        return actual_inv

    def compute_output_elasticity(self, k):
        """
        Return elasticity of output with respect to capital stock (per unit
        effective labor).

        Parameters
        ----------
        k : array_like (float)
            Capital stock (per unit of effective labor)

        Returns
        -------
        alpha_k : array_like (float)
            Elasticity of output with respect to capital stock (per unit
            effective labor).

        Notes
        -----
        Under the additional assumption that markets are perfectly competitive,
        the elasticity of output with respect to capital stock is equivalent to
        capital's share of income. Since, under perfect competition, firms earn
        zero profits it must be true capital's share and labor's share must sum
        to one.

        """
        alpha_k = (k * self.compute_mpk(k)) / self.compute_intensive_output(k)
        return alpha_k

    def compute_effective_depreciation(self, k):
        """
        Return amount of Capital stock (per unit of effective labor) that
        depreciaties due to technological progress, population growth, and
        physical depreciation.

        Parameters
        ----------
        k : array_like (float)
            Capital stock (per unit of effective labor)

        Returns
        -------
        effective_depreciation : array_like (float)
            Amount of depreciated Capital stock (per unit of effective labor)

        """
        effective_depreciation = self.effective_depreciation_rate * k
        return effective_depreciation

    def compute_intensive_output(self, k):
        """
        Return the amount of output (per unit of effective labor).

        Parameters
        ----------
        k : ndarray (float)
            Capital stock (per unit of effective labor)

        Returns
        -------
        y : ndarray (float)
            Output (per unit of effective labor)

        """
        y = self._intensive_output(k, **self.params)
        return y

    def compute_k_dot(self, k):
        """
        Return time derivative of capital stock (per unit of effective labor).

        Parameters
        ----------
        k : ndarray (float)
            Capital stock (per unit of effective labor)

        Returns
        -------
        k_dot : ndarray (float)
            Time derivative of capital stock (per unit of effective labor).

        """
        k_dot = (self.compute_actual_investment(k) -
                 self.compute_effective_depreciation(k))
        return k_dot

    def compute_mpk(self, k):
        """
        Return marginal product of capital stock (per unit of effective labor).

        Parameters
        ----------
        k : ndarray (float)
            Capital stock (per unit of effective labor)

        Returns
        -------
        mpk : ndarray (float)
            Marginal product of capital stock (per unit of effective labor).

        """
        mpk = self._mpk(k, **self.params)
        return mpk

    def find_steady_state(self, a, b, method='brentq', **kwargs):
        """
        Compute the equilibrium value of capital stock (per unit effective
        labor).

        Parameters
        ----------
        a : float
            One end of the bracketing interval [a,b].
        b : float
            The other end of the bracketing interval [a,b]
        method : str (default=`brentq`)
            Method to use when computing the steady state. Supported methods
            are `bisect`, `brenth`, `brentq`, `ridder`. See `scipy.optimize`
            for more details (including references).
        kwargs : optional
            Additional keyword arguments. Keyword arguments are method specific
            see `scipy.optimize` for details.

        Returns
        -------
        x0 : float
            Zero of `f` between `a` and `b`.
        r : RootResults (present if ``full_output = True``)
            Object containing information about the convergence. In particular,
            ``r.converged`` is True if the routine converged.

        """
        if method == 'bisect':
            result = optimize.bisect(self.compute_k_dot, a, b, **kwargs)
        elif method == 'brenth':
            result = optimize.brenth(self.compute_k_dot, a, b, **kwargs)
        elif method == 'brentq':
            result = optimize.brentq(self.compute_k_dot, a, b, **kwargs)
        elif method == 'ridder':
            result = optimize.ridder(self.compute_k_dot, a, b, **kwargs)
        else:
            mesg = ("Method must be one of : 'bisect', 'brenth', 'brentq', " +
                    "or 'ridder'.")
            raise ValueError(mesg)

        return result


def plot_intensive_output(cls, Nk=1e3, k_upper=10, **new_params):
    """
    Plot intensive form of the aggregate production function.

    Parameters
    ----------
    cls : object
        An instance of :class:`quantecon.models.solow.model.Model`.
    Nk : float
        Number of capital stock (per unit of effective labor) grid points to
        plot.
    k_upper : float
        Upper bound on capital stock (per unit of effective labor) for the
        plot.
    new_params : dict (optional)
        Optional dictionary of parameter values to change.

    Returns
    -------
    A list containing:

    fig : object
        An instance of :class:`matplotlib.figure.Figure`.
    ax : object
        An instance of :class:`matplotlib.axes.AxesSubplot`.

    """
    # update model parameters
    cls.params.update(new_params)

    # create the plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), squeeze=True)
    k_grid = np.linspace(0, k_upper, Nk)
    ax.plot(k_grid, cls.compute_intensive_output(k_grid), 'r-')
    ax.set_xlabel('Capital (per unit effective labor), $k(t)$', family='serif',
                  fontsize=15)
    ax.set_ylabel('$f(k(t))$', family='serif', fontsize=20,
                  rotation='horizontal')
    ax.yaxis.set_label_coords(-0.1, 0.5)
    ax.set_title('Output (per unit effective labor)',
                 family='serif', fontsize=20)
    ax.grid(True)

    return [fig, ax]


def plot_factor_shares(cls, Nk=1e3, k_upper=10, **new_params):
    """
    Plot income/output shares of capital and labor inputs to production.

    Parameters
    ----------
    cls : object
        An instance of :class:`quantecon.models.solow.model.Model`.
    Nk : float
        Number of capital stock (per unit of effective labor) grid points to
        plot.
    k_upper : float
        Upper bound on capital stock (per unit of effective labor) for the
        plot.
    new_params : dict (optional)
        Optional dictionary of parameter values to change.

    Returns
    -------
    A list containing:

    fig : object
        An instance of :class:`matplotlib.figure.Figure`.
    ax : object
        An instance of :class:`matplotlib.axes.AxesSubplot`.

    """
    # update the model parameters
    cls.params.update(new_params)

    # create the plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), squeeze=True)
    k_grid = np.linspace(0, k_upper, Nk)
    capitals_share = cls.compute_output_elasticity(k_grid)
    labors_share = 1 - capitals_share

    ax.plot(k_grid, capitals_share, 'r-', label='$\alpha_K(t)$')
    ax.plot(k_grid, labors_share, 'b-', label='$1 - \alpha_K(t)$')
    ax.set_xlabel('Capital (per unit effective labor), $k(t)$', family='serif',
                  fontsize=15)
    ax.set_title('Factor shares', family='serif', fontsize=20)
    ax.grid(True)
    ax.legend(loc=0, frameon=False, prop={'family': 'serif'},
              bbox_to_anchor=(1.0, 1.0))

    return [fig, ax]


def plot_intensive_investment(cls, Nk=1e3, k_upper=10, **new_params):
    """
    Plot actual investment (per unit effective labor) and effective
    depreciation. The steady state value of capital stock (per unit effective
    labor) balance acual investment and effective depreciation.

    Parameters
    ----------
    cls : object
        An instance of :class:`quantecon.models.solow.model.Model`.
    Nk : float
        Number of capital stock (per unit of effective labor) grid points to
        plot.
    k_upper : float
        Upper bound on capital stock (per unit of effective labor) for the
        plot.
    new_params : dict (optional)
        Optional dictionary of parameter values to change.

    Returns
    -------
    A list containing:

    fig : object
        An instance of :class:`matplotlib.figure.Figure`.
    ax : object
        An instance of :class:`matplotlib.axes.AxesSubplot`.

    """
    # update the model parameters
    cls.params.update(new_params)

    # solve for the steady state
    eps = 1e-6
    k_star = cls.find_steady_state(eps, k_upper)

    # create the plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), squeeze=True)
    k_grid = np.linspace(0, k_upper, Nk)
    ax.plot(k_grid, cls.compute_actual_investment(k_grid), 'g-',
            label='$sf(k(t))$')
    ax.plot(k_grid, cls.compute_effective_depreciation(k_grid), 'b-',
            label='$(g + n + \delta)k(t)$')
    ax.plot(k_star, cls.compute_actual_investment(k_star), 'ko',
            label='$k^*={0:.4f}$'.format(k_star))
    ax.set_xlabel('Capital (per unit effective labor), $k(t)$', family='serif',
                  fontsize=15)
    ax.set_ylabel('Investment (per unit effective labor)', family='serif',
                  fontsize=15)
    ax.set_title('Output (per unit effective labor)',
                 family='serif', fontsize=20)
    ax.grid(True)
    ax.legend(loc=0, frameon=False, prop={'family': 'serif'},
              bbox_to_anchor=(1.0, 1.0))

    return [fig, ax]


def plot_phase_diagram(cls, Nk=1e3, k_upper=10, **new_params):
    """
    Plot the model's phase diagram.

    Parameters
    ----------
    cls : object
        An instance of :class:`quantecon.models.solow.model.Model`.
    Nk : float
        Number of capital stock (per unit of effective labor) grid points to
        plot.
    k_upper : float
        Upper bound on capital stock (per unit of effective labor) for the
        plot.
    new_params : dict (optional)
        Optional dictionary of parameter values to change.

    Returns
    -------
    A list containing:

    fig : object
        An instance of :class:`matplotlib.figure.Figure`.
    ax : object
        An instance of :class:`matplotlib.axes.AxesSubplot`.

    """
    # update model parameters
    cls.params.update(new_params)

    # solve for the steady state
    eps = 1e-6
    k_star = cls.find_steady_state(eps, k_upper)

    # create the plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), squeeze=True)
    k_grid = np.linspace(0, k_upper, Nk)
    ax.plot(k_grid, cls.compute_k_dot(k_grid), color='orange')
    ax.axhline(0, color='k')
    ax.plot(k_star, 0.0, 'ko', label='$k^*={0:.4f}$'.format(k_star))
    ax.set_xlabel('Capital (per unit effective labor), $k(t)$', family='serif',
                  fontsize=15)
    ax.set_ylabel('$\dot{k}(t)$', family='serif', fontsize=25,
                  rotation='horizontal')
    ax.yaxis.set_label_coords(-0.1, 0.5)
    ax.set_title('Phase diagram', family='serif', fontsize=20)
    ax.grid(True)

    return [fig, ax]


def plot_solow_diagram(cls, Nk=1e3, k_upper=10, **new_params):
    """
    Plot the classic Solow diagram.

    Parameters
    ----------
    cls : object
        An instance of :class:`quantecon.models.solow.model.Model`.
    Nk : float
        Number of capital stock (per unit of effective labor) grid points to
        plot.
    k_upper : float
        Upper bound on capital stock (per unit of effective labor) for the
        plot.
    new_params : dict (optional)
        Optional dictionary of parameter values to change.

    Returns
    -------
    A list containing:

    fig : object
        An instance of :class:`matplotlib.figure.Figure`.
    ax : object
        An instance of :class:`matplotlib.axes.AxesSubplot`.

    """
    # update the model parameters
    cls.params.update(new_params)

    # solve for the steady state
    eps = 1e-6
    k_star = cls.find_steady_state(eps, k_upper)

    # create the plot
    fig, ax = plt.subplots(1, 1, figsize=(8, 6), squeeze=True)
    k_grid = np.linspace(0, k_upper, Nk)
    ax.plot(k_grid, cls.compute_intensive_output(k_grid), 'r-',
            label='$f(k(t)$')
    ax.plot(k_grid, cls.compute_actual_investment(k_grid), 'g-',
            label='$sf(k(t))$')
    ax.plot(k_grid, cls.compute_effective_depreciation(k_grid), 'b-',
            label='$(g + n + \delta)k(t)$')
    ax.plot(k_star, cls.compute_actual_investment(k_star), 'ko',
            label='$k^*={0:.4f}$'.format(k_star))
    ax.set_xlabel('Capital (per unit effective labor), $k(t)$', family='serif',
                  fontsize=15)
    ax.set_title('Solow diagram',
                 family='serif', fontsize=20)
    ax.grid(True)
    ax.legend(loc=0, frameon=False, prop={'family': 'serif'},
              bbox_to_anchor=(1, 1))

    return [fig, ax]
