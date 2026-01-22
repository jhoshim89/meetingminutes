import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class PinLoginScreen extends StatefulWidget {
  final VoidCallback onLoginSuccess;

  const PinLoginScreen({
    Key? key,
    required this.onLoginSuccess,
  }) : super(key: key);

  @override
  State<PinLoginScreen> createState() => _PinLoginScreenState();
}

class _PinLoginScreenState extends State<PinLoginScreen> {
  String _pin = '';
  String? _errorMessage;
  bool _isLoading = false;

  static const int _pinLength = 4;

  void _onKeyTap(String key) {
    if (_pin.length < _pinLength) {
      setState(() {
        _pin += key;
        _errorMessage = null;
      });

      // 4자리 입력 완료 시 자동 로그인 시도
      if (_pin.length == _pinLength) {
        _attemptLogin();
      }
    }
  }

  void _onBackspace() {
    if (_pin.isNotEmpty) {
      setState(() {
        _pin = _pin.substring(0, _pin.length - 1);
        _errorMessage = null;
      });
    }
  }

  void _onClear() {
    setState(() {
      _pin = '';
      _errorMessage = null;
    });
  }

  Future<void> _attemptLogin() async {
    if (_isLoading) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final success = await authProvider.signInWithPin(_pin);

    if (mounted) {
      setState(() {
        _isLoading = false;
      });

      if (success) {
        widget.onLoginSuccess();
      } else {
        setState(() {
          _pin = '';
          _errorMessage = 'Invalid PIN. Please try again.';
        });
        // 진동 피드백 (웹에서는 무시됨)
        HapticFeedback.heavyImpact();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(flex: 2),

            // 앱 로고/아이콘
            Icon(
              Icons.mic_rounded,
              size: 64,
              color: Theme.of(context).primaryColor,
            ),
            const SizedBox(height: 16),

            // 앱 이름
            Text(
              'Meeting Minutes',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),

            // 안내 메시지
            Text(
              'Enter PIN to continue',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),

            const SizedBox(height: 40),

            // PIN 표시기
            _buildPinIndicator(),

            const SizedBox(height: 16),

            // 에러 메시지
            SizedBox(
              height: 24,
              child: _errorMessage != null
                  ? Text(
                      _errorMessage!,
                      style: const TextStyle(
                        color: Colors.red,
                        fontSize: 14,
                      ),
                    )
                  : null,
            ),

            // 로딩 표시
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),

            const Spacer(flex: 1),

            // 숫자 키패드
            _buildKeypad(isDark),

            const Spacer(flex: 1),
          ],
        ),
      ),
    );
  }

  Widget _buildPinIndicator() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(_pinLength, (index) {
        final isFilled = index < _pin.length;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 12),
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isFilled
                ? Theme.of(context).primaryColor
                : Colors.transparent,
            border: Border.all(
              color: Theme.of(context).primaryColor,
              width: 2,
            ),
          ),
        );
      }),
    );
  }

  Widget _buildKeypad(bool isDark) {
    final buttonColor = isDark ? const Color(0xFF2C2C2C) : Colors.grey[100];
    final textColor = isDark ? Colors.white : Colors.black87;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 48),
      child: Column(
        children: [
          // 1, 2, 3
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildKeyButton('1', buttonColor!, textColor),
              _buildKeyButton('2', buttonColor, textColor),
              _buildKeyButton('3', buttonColor, textColor),
            ],
          ),
          const SizedBox(height: 16),
          // 4, 5, 6
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildKeyButton('4', buttonColor, textColor),
              _buildKeyButton('5', buttonColor, textColor),
              _buildKeyButton('6', buttonColor, textColor),
            ],
          ),
          const SizedBox(height: 16),
          // 7, 8, 9
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildKeyButton('7', buttonColor, textColor),
              _buildKeyButton('8', buttonColor, textColor),
              _buildKeyButton('9', buttonColor, textColor),
            ],
          ),
          const SizedBox(height: 16),
          // Clear, 0, Backspace
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildActionButton(
                icon: Icons.clear,
                onTap: _onClear,
                color: buttonColor,
              ),
              _buildKeyButton('0', buttonColor, textColor),
              _buildActionButton(
                icon: Icons.backspace_outlined,
                onTap: _onBackspace,
                color: buttonColor,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildKeyButton(String digit, Color bgColor, Color textColor) {
    return Material(
      color: bgColor,
      borderRadius: BorderRadius.circular(40),
      child: InkWell(
        onTap: _isLoading ? null : () => _onKeyTap(digit),
        borderRadius: BorderRadius.circular(40),
        child: Container(
          width: 72,
          height: 72,
          alignment: Alignment.center,
          child: Text(
            digit,
            style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w500,
              color: _isLoading ? textColor.withOpacity(0.5) : textColor,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required VoidCallback onTap,
    required Color color,
  }) {
    return Material(
      color: color,
      borderRadius: BorderRadius.circular(40),
      child: InkWell(
        onTap: _isLoading ? null : onTap,
        borderRadius: BorderRadius.circular(40),
        child: Container(
          width: 72,
          height: 72,
          alignment: Alignment.center,
          child: Icon(
            icon,
            size: 24,
            color: _isLoading ? Colors.grey : null,
          ),
        ),
      ),
    );
  }
}
